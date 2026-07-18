from database import tool_conn
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

load_dotenv()

api_key=os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    api_key=api_key,
    temperature=0,
)




def extract_memory(user_message):

    prompt = f"""
You are a memory extractor.

Your job is to identify ONLY long-term facts about the user.

Store things like

- Name
- Age
- Birthday
- City
- College
- Job
- Profession
- Favourite language
- Favourite framework
- Favourite food
- Goals
- Interests

Do NOT store

- Greetings
- Temporary requests
- Questions
- Calculations
- Small talk

If nothing should be remembered

Return ONLY

NONE


User:

{user_message}
"""

    response = llm.invoke(
        [HumanMessage(content=prompt)]
    )

    return response.content.strip()

def save_memory(user_id, memory):

    tool_conn.execute(
        """
        INSERT INTO memories(
            user_id,
            memory
        )
        VALUES(?,?)
        """,
        (
            user_id,
            memory
        )
    )

    tool_conn.commit()


def get_memories(user_id):

    cursor = tool_conn.execute(
        """
        SELECT memory
        FROM memories
        WHERE user_id=?
        ORDER BY created_at
        """,
        (user_id,)
    )

    return [row[0] for row in cursor.fetchall()]