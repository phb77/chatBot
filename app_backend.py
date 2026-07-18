from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated ,NotRequired
from langchain_core.messages import BaseMessage, HumanMessage , SystemMessage ,AIMessage,ToolMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from database import checkpointer , tool_conn
from tools import tools
from langsmith import traceable
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode,tools_condition
from memory import get_memories
import os


load_dotenv()

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT")

api_key = os.getenv("OPENAI_API_KEY")


load_dotenv()

# llm = ChatGroq(
#     model="llama-3.3-70b-versatile",
#     api_key=api_key,
#     temperature=0,
    
# )
# title_llm = ChatGroq(
#     model="llama-3.3-70b-versatile",
#     api_key=api_key,
#     temperature=0
# )
# summary_llm = ChatGroq(
#     model="llama-3.3-70b-versatile",
#     api_key=api_key,
#     temperature=0
# )

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    api_key=api_key,
    temperature=0,
)

# Title generation
title_llm = ChatOpenAI(
    model="gpt-4.1-mini",
    api_key=api_key,
    temperature=0,
)

# Conversation summary
summary_llm = ChatOpenAI(
    model="gpt-4.1-mini",
    api_key=api_key,
    temperature=0,
)


llm = llm.bind_tools(tools , tool_choice="auto")



"""
messages is a list.
Each element is a message object (HumanMessage, AIMessage, ToolMessage, SystemMessage, etc.).
Use add_messages to append/merge new messages into the existing conversation history instead of replacing it.
"""

class Chat(TypedDict) :
    messages : Annotated[list[BaseMessage] , add_messages]
    summary: NotRequired[str]
    summarized_count: NotRequired[int]

@traceable(name="Conversation Summary")
def create_conversation_summary(
    old_summary: str,
    messages: list[BaseMessage]
) -> str:

    if not messages:
        return old_summary

    conversation_text = []

    for message in messages:

        if isinstance(message, HumanMessage):

            if message.content:
                conversation_text.append(
                    f"User: {message.content}"
                )

        elif isinstance(message, AIMessage):

            # Ignore AI messages that only request tools
            if getattr(message, "tool_calls", None):
                continue

            if message.content:
                conversation_text.append(
                    f"Assistant: {message.content}"
                )

        elif isinstance(message, ToolMessage):

            # Do not put raw tool results in summary
            continue

    prompt = f"""
You maintain a concise summary of a conversation.

Existing summary:
{old_summary}

New conversation messages:
{chr(10).join(conversation_text)}

Create an updated concise summary containing important
conversation context, decisions, questions, and information
needed to continue the conversation.

Do not include unnecessary details.
Return only the updated summary.
"""

    response = summary_llm.invoke(
        [HumanMessage(content=prompt)],
        config={
            "tags": ["summary_llm"]
        }
    )

    return response.content.strip()

def get_safe_recent_messages(
    messages: list[BaseMessage],
    keep_recent: int = 3
) -> list[BaseMessage]:
    """
    Return recent messages without breaking
    AI tool_call -> ToolMessage sequences.
    """

    # If history is already small,
    # return everything
    if len(messages) <= keep_recent:
        return messages


    # Normal starting position
    start_index = len(messages) - keep_recent


    # ------------------------------------------------
    # If we are starting from ToolMessage,
    # move backward until we find the AIMessage
    # that requested the tool call.
    # ------------------------------------------------

    while (
        start_index > 0
        and isinstance(
            messages[start_index],
            ToolMessage
        )
    ):
        start_index -= 1


    # ------------------------------------------------
    # We may now be at an AIMessage with tool_calls.
    # That's valid, so keep it.
    #
    # But if the message immediately before our
    # starting point is AIMessage with tool_calls,
    # we also need to include it because the current
    # messages may contain its ToolMessage.
    # ------------------------------------------------

    if start_index > 0:

        previous_message = messages[
            start_index - 1
        ]

        current_message = messages[
            start_index
        ]

        if (
            isinstance(
                current_message,
                ToolMessage
            )
            and isinstance(
                previous_message,
                AIMessage
            )
            and previous_message.tool_calls
        ):
            start_index -= 1


    return messages[start_index:]

@traceable(name="Chat Node")
def chat_node(
    state: Chat,
    config: RunnableConfig
):

    messages = state["messages"]

    summary = state.get(
        "summary",
        ""
    )

    summarized_count = state.get(
        "summarized_count",
        0
    )

    KEEP_RECENT = 3


    # ==================================================
    # 1. GET USER ID
    # ==================================================

    user_id = config["configurable"]["user_id"]


    # ==================================================
    # 2. LOAD LONG-TERM MEMORY FROM DATABASE
    # ==================================================

    memories = get_memories(user_id)

    memory_text = ""

    if memories:

        memory_text = "\n".join(
            f"- {memory}"
            for memory in memories
        )


    # ==================================================
    # 3. GET SAFE RECENT MESSAGES
    # ==================================================

    recent_messages = get_safe_recent_messages(
        messages,
        KEEP_RECENT
    )


    # ==================================================
    # 4. CALCULATE MESSAGES TO SUMMARIZE
    # ==================================================

    summarize_until = (
        len(messages)
        - len(recent_messages)
    )


    new_messages_to_summarize = messages[
        summarized_count:summarize_until
    ]


    # ==================================================
    # 5. UPDATE CONVERSATION SUMMARY
    # ==================================================

    if new_messages_to_summarize:

        summary = create_conversation_summary(
            summary,
            new_messages_to_summarize
        )

        summarized_count = summarize_until


    # ==================================================
    # 6. BUILD LLM CONTEXT
    # ==================================================

    llm_messages = []


    # ------------------------------------------
    # Long-term memory
    # ------------------------------------------

    if memory_text:

        llm_messages.append(
            SystemMessage(
                content=f"""
You have the following long-term memories about the current user:

{memory_text}

Use these memories when answering questions about the user.

For example:
- If the user's name is stored and they ask "What is my name?",
  answer using the stored name.
- If their college is stored and they ask about their college,
  use the stored information.

Do not say you do not know information that is explicitly available
in these memories.

whenever you call ant tool : 
- Use ONLY the tool results.
- Do NOT mix your own knowledge.
- If publication dates are available, always prefer the newest.
- Never invent dates.
- If the search results are old, clearly say they are old.
"""
            )
        )


    # ------------------------------------------
    # Conversation summary
    # ------------------------------------------

    if summary:

        llm_messages.append(
            SystemMessage(
                content=f"""
Summary of earlier messages in the current conversation:

{summary}

Use this summary to maintain continuity in the current conversation.
"""
            )
        )


    # ------------------------------------------
    # Recent messages
    # ------------------------------------------

    llm_messages.extend(
        recent_messages
    )


    # ==================================================
    # 7. CALL LLM
    # ==================================================

    try:

        response = llm.invoke(
            llm_messages,
            config=config
        )

        return {
            "messages": [response],
            "summary": summary,
            "summarized_count": summarized_count
        }

    except Exception as e:

        print("\n" + "=" * 80)
        print("LLM ERROR TYPE:", type(e).__name__)
        print("LLM ERROR:", str(e))

        if hasattr(e, "body"):
            print("ERROR BODY:", e.body)

            if isinstance(e.body, dict):
                error = e.body.get("error", {})

                print(
                    "FAILED GENERATION:",
                    error.get("failed_generation")
                )

        print("=" * 80 + "\n")

        raise

@traceable(name="Generate Chat Title")
def generate_chat_title(user_message: str) -> str:

    prompt = f"""
    You generate titles for chat conversations.

    Rules:
    - Return ONLY the title.
    - Maximum 5 words.
    - No quotation marks.
    - No full stop.
    - No markdown.
    - Do not write "Chat" or "Conversation".

    User message:
    {user_message}
    """

    response = title_llm.invoke(
        [HumanMessage(content=prompt)]
    )

    return response.content.strip()


def save_thread_title(thread_id,user_id, title):

    tool_conn.execute(
        """
        INSERT OR REPLACE INTO threads(
                thread_id,
                user_id,
                title,
                pdf_name
            )
            VALUES(?,?,?,COALESCE(
            (
            SELECT pdf_name
            FROM threads
            WHERE thread_id=?
            ),
            NULL
            ))
            """,
            (thread_id, user_id, title, thread_id)
    )

    tool_conn.commit()

def delete_thread(thread_id,user_id):

    tool_conn.execute(
        """
        DELETE FROM threads
        WHERE thread_id=?
        AND user_id=?
        """,
        (
            thread_id,
            user_id
        )
    )

    tool_conn.commit()


tool_node = ToolNode(tools)

graph = StateGraph(Chat) 
graph.add_node("chat_node" , chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START , "chat_node")
graph.add_conditional_edges("chat_node" , tools_condition)
graph.add_edge("tools","chat_node")

chatbot = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads(user_id):

    cursor=tool_conn.execute(
        """
        SELECT thread_id,title
        FROM threads
        WHERE user_id=?
        ORDER BY rowid DESC
        """,
        (user_id,)
    )

    return cursor.fetchall()

def save_pdf_name(
    thread_id,
    user_id,
    pdf_name
):

    tool_conn.execute(
        """
        UPDATE threads
        SET pdf_name=?
        WHERE thread_id=?
        AND user_id=?
        """,
        (
            pdf_name,
            thread_id,
            user_id
        )
    )

    tool_conn.commit()


def get_pdf_name(
    thread_id,
    user_id
):

    cursor=tool_conn.execute(
        """
        SELECT pdf_name
        FROM threads
        WHERE
        thread_id=?
        AND user_id=?
        """,
        (
            thread_id,
            user_id
        )
    )

    row=cursor.fetchone()

    if row:
        return row[0]

    return None

def clear_pdf_info(
    thread_id,
    user_id
):

    tool_conn.execute(
        """
        UPDATE threads
        SET pdf_name=NULL
        WHERE thread_id=?
        AND user_id=?
        """,
        (
            thread_id,
            user_id
        )
    )

    tool_conn.commit()
