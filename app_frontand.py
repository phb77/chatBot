import streamlit as st
from app_backend import (
    chatbot,
    retrieve_all_threads,
    generate_chat_title,
    save_thread_title,
    delete_thread,
    save_pdf_name,
    get_pdf_name,
    clear_pdf_info
)
from langchain_core.messages import HumanMessage, AIMessage
import uuid
from rag import create_vectorstore
import os
import shutil
from auth import auth_page, register_user, login_user
from memory import extract_memory, save_memory


# ============================================================
# INITIALIZE LOGIN STATE
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False


# ============================================================
# LOGIN / SIGNUP PAGE
# ============================================================

if not st.session_state["logged_in"]:

    option, email, password, submit = auth_page()

    # ---------------- LOGIN ----------------

    if option == "login" and submit:

        user_id = login_user(
            email,
            password
        )

        if user_id is None:

            st.error(
                "Invalid Email or Password. "
                "Please sign up first."
            )

        else:

            st.session_state["logged_in"] = True
            st.session_state["user_id"] = user_id
            st.session_state["email"] = email

            st.rerun()


    # ---------------- SIGN UP ----------------

    elif option == "signup" and submit:

        success, message = register_user(
            email,
            password
        )

        if success:
            st.success(message)
        else:
            st.error(message)


    # Stop chatbot UI until login
    st.stop()




st.title("ChatBottt")

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def generate_thread_id():

    return str(uuid.uuid4())


def reset_chat():

    thread_id = generate_thread_id()

    st.session_state["thread_id"] = thread_id
    st.session_state["message_history"] = []

    save_thread_title(
        thread_id,
        st.session_state["user_id"],
        "New Chat"
    )


def load_conversation(thread_id):

    state = chatbot.get_state(
        config={
            "configurable": {
                "thread_id": thread_id,
                "user_id": st.session_state["user_id"]
            }
        }
    )

    return state.values.get(
        "messages",
        []
    )


# ============================================================
# INITIALIZE CHAT STATE
# ============================================================

if "message_history" not in st.session_state:

    st.session_state["message_history"] = []


if "thread_id" not in st.session_state:

    thread_id = generate_thread_id()

    st.session_state["thread_id"] = thread_id

    save_thread_title(
        thread_id,
        st.session_state["user_id"],
        "New Chat"
    )


# ============================================================
# SIDEBAR USER
# ============================================================

# ============================================================
# USERNAME BOX - TOP SIDEBAR
# ============================================================

username = st.session_state.get(
    "username",
    "User"
)

st.sidebar.markdown(
    f"""
    <div style="
        background-color: rgba(255, 255, 0, 0.15);
        padding: 14px 10px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    ">
        <span style="
            font-size: 16px;
            font-weight: 600;
        ">
             Welcome to ChatBottt
        </span>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR TITLE
# ============================================================

st.sidebar.title(
    "LangGraph Chatbot"
)


# ============================================================
# NEW CHAT BUTTON
# ============================================================

if st.sidebar.button(
    "➕ New Chat",
    key="new_chat_button"
):

    reset_chat()

    st.rerun()


# ============================================================
# PDF SECTION
# ============================================================

pdf_name = get_pdf_name(
    st.session_state["thread_id"],
    st.session_state["user_id"]
)


if pdf_name is None:

    uploaded_file = st.sidebar.file_uploader(
        "Upload PDF",
        type=["pdf"]
    )

    if uploaded_file:

        # Separate upload folder for each user
        folder = os.path.join(
            "uploads",
            str(st.session_state["user_id"])
        )

        os.makedirs(
            folder,
            exist_ok=True
        )

        pdf_path = os.path.join(
            folder,
            uploaded_file.name
        )

        with open(
            pdf_path,
            "wb"
        ) as f:

            f.write(
                uploaded_file.getbuffer()
            )


        # Create embeddings
        with st.spinner(
            "Creating embeddings..."
        ):

            success = create_vectorstore(
                pdf_path,
                st.session_state["user_id"],
                st.session_state["thread_id"]
            )


        if success:

            save_pdf_name(
                st.session_state["thread_id"],
                st.session_state["user_id"],
                uploaded_file.name
            )

            st.sidebar.success(
                "PDF uploaded successfully"
            )

            st.rerun()

        else:

            st.sidebar.error(
                "Unable to process PDF."
            )


else:

    st.sidebar.success(
        "📄 PDF uploaded"
    )

    st.sidebar.write(
        pdf_name
    )


    # ========================================================
    # CHANGE PDF
    # ========================================================

    if st.sidebar.button(
        "🔄 Change PDF",
        key="change_pdf_button"
    ):

        vectorstore_path = os.path.join(
            "vectorstore",
            str(st.session_state["user_id"]),
            st.session_state["thread_id"]
        )

        if os.path.exists(
            vectorstore_path
        ):

            shutil.rmtree(
                vectorstore_path
            )


        clear_pdf_info(
            st.session_state["thread_id"],
            st.session_state["user_id"]
        )

        st.rerun()


# ============================================================
# CONVERSATION HISTORY
# ============================================================

st.sidebar.header(
    "My Conversations"
)


for thread_id, title in retrieve_all_threads(
    st.session_state["user_id"]
):

    col1, col2 = st.sidebar.columns(
        [3, 1],
        gap="small"
    )


    # ========================================================
    # OPEN CONVERSATION
    # ========================================================

    if col1.button(
        title,
        key=f"thread_{thread_id}"
    ):

        st.session_state[
            "thread_id"
        ] = thread_id

        messages = load_conversation(
            thread_id
        )

        temp_messages = []


        for msg in messages:

            if isinstance(
                msg,
                HumanMessage
            ):

                role = "user"


            elif isinstance(
                msg,
                AIMessage
            ):

                if (
                    not msg.content
                    or
                    not str(
                        msg.content
                    ).strip()
                ):

                    continue

                role = "assistant"


            else:

                continue


            temp_messages.append(
                {
                    "role": role,
                    "content": msg.content
                }
            )


        st.session_state[
            "message_history"
        ] = temp_messages

        st.rerun()


    # ========================================================
    # DELETE CONVERSATION
    # ========================================================

    if col2.button(
        "❌",
        key=f"delete_{thread_id}"
    ):

        delete_thread(
            thread_id,
            st.session_state["user_id"]
        )


        # Delete vectorstore
        vectorstore_path = os.path.join(
            "vectorstore",
            str(st.session_state["user_id"]),
            thread_id
        )


        if os.path.exists(
            vectorstore_path
        ):

            shutil.rmtree(
                vectorstore_path
            )


        remaining_threads = retrieve_all_threads(
            st.session_state["user_id"]
        )


        # If current thread was deleted
        if (
            st.session_state["thread_id"]
            == thread_id
        ):

            if remaining_threads:

                new_thread_id = remaining_threads[0][0]

                st.session_state[
                    "thread_id"
                ] = new_thread_id

                messages = load_conversation(
                    new_thread_id
                )

                temp_messages = []

                for msg in messages:

                    if isinstance(
                        msg,
                        HumanMessage
                    ):

                        role = "user"


                    elif isinstance(
                        msg,
                        AIMessage
                    ):

                        if (
                            not msg.content
                            or
                            not str(
                                msg.content
                            ).strip()
                        ):

                            continue

                        role = "assistant"

                    else:

                        continue


                    temp_messages.append(
                        {
                            "role": role,
                            "content": msg.content
                        }
                    )


                st.session_state[
                    "message_history"
                ] = temp_messages


            else:

                new_thread_id = generate_thread_id()

                st.session_state[
                    "thread_id"
                ] = new_thread_id

                st.session_state[
                    "message_history"
                ] = []


                save_thread_title(
                    new_thread_id,
                    st.session_state["user_id"],
                    "New Chat"
                )


        st.rerun()


# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================

for message in st.session_state[
    "message_history"
]:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# ============================================================
# CHAT INPUT
# ============================================================

user_input = st.chat_input(
    "Type here"
)


if user_input:


    # ========================================================
    # GENERATE TITLE FOR FIRST MESSAGE
    # ========================================================

    if len(
        st.session_state[
            "message_history"
        ]
    ) == 0:

        save_thread_title(
            st.session_state["thread_id"],
            st.session_state["user_id"],
            "New Chat"
        )


        title = generate_chat_title(
            user_input
        )


        save_thread_title(
            st.session_state["thread_id"],
            st.session_state["user_id"],
            title
        )


    # ========================================================
    # ADD USER MESSAGE TO UI
    # ========================================================

    st.session_state[
        "message_history"
    ].append(
        {
            "role": "user",
            "content": user_input
        }
    )


    with st.chat_message(
        "user"
    ):

        st.markdown(
            user_input
        )


    # ========================================================
    # EXTRACT LONG-TERM MEMORY
    # ========================================================

    try:

        memory = extract_memory(
            user_input
        )


        if (
            memory
            and
            memory.strip().upper()
            != "NONE"
        ):

            save_memory(
                st.session_state["user_id"],
                memory
            )


    except Exception as e:

        print(
            "MEMORY EXTRACTION ERROR:",
            e
        )


    # ========================================================
    # LANGGRAPH CONFIG
    # ========================================================

    CONFIG = {

        "configurable": {

            "thread_id":
                st.session_state["thread_id"],

            "user_id":
                st.session_state["user_id"]
        },

        "metadata": {

            "thread_id":
                st.session_state["thread_id"],

            "user_id":
                st.session_state["user_id"]
        },

        "run_name":
            "chat_turn",
    }


    # ========================================================
    # ASSISTANT RESPONSE
    # ========================================================

    with st.chat_message("assistant"):

        def ai_only_stream():

            for message_chunk, metadata in chatbot.stream(
                {
                    "messages": [
                        HumanMessage(
                            content=user_input
                        )
                    ]
                },
                config=CONFIG,
                stream_mode="messages",
            ):

                # IMPORTANT: define tags first
                tags = metadata.get("tags", [])

                # Stream only main chatbot response
                # Ignore summary LLM output
                if (
                    metadata.get("langgraph_node") == "chat_node"
                    and "summary_llm" not in tags
                    and isinstance(message_chunk, AIMessage)
                    and message_chunk.content
                    and str(message_chunk.content).strip()
                ):

                    yield message_chunk.content


        ai_message = st.write_stream(
            ai_only_stream()
        )


    # ========================================================
    # SAVE ASSISTANT MESSAGE
    # ========================================================

    if ai_message:

        st.session_state[
            "message_history"
        ].append(
            {
                "role": "assistant",
                "content": ai_message
            }
        )


# ============================================================
# LOGOUT SECTION
# ============================================================

# Add empty space before logout.
# IMPORTANT:
# We removed your old CSS using:
# .stButton:last-of-type
#
# That CSS could affect New Chat and conversation buttons.

# ============================================================
# FIXED LOGOUT BUTTON - BOTTOM RIGHT
# ============================================================

# Place this AFTER login check but BEFORE your chat messages

logout_placeholder = st.empty()

with logout_placeholder.container():

    st.markdown(
        """
        <style>
        /* Target logout button using its Streamlit key */
        div[data-testid="stButton"]:has(button[kind="secondary"]) {
        }

        .st-key-logout_fixed {
            position: fixed !important;
            right: 25px !important;
            bottom: 25px !important;
            top: auto !important;
            left: auto !important;
            width: 130px !important;
            z-index: 999999 !important;
        }

        .st-key-logout_fixed > div {
            width: 130px !important;
        }

        .st-key-logout_fixed button {
            width: 130px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    logout = st.button(
        "🚪 Logout",
        key="logout_fixed"
    )


if logout:

    st.session_state["logged_in"] = False

    st.session_state.pop("user_id", None)
    st.session_state.pop("username", None)
    st.session_state.pop("thread_id", None)
    st.session_state.pop("message_history", None)

    st.rerun()