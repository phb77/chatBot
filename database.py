import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect(
    "chatbot.db",
    check_same_thread=False
)

checkpointer = SqliteSaver(conn=conn)

tool_conn = sqlite3.connect(
    "chatbot.db",
    check_same_thread=False
)

# tool_conn.execute("""
# CREATE TABLE IF NOT EXISTS users(
#     user_id INTEGER PRIMARY KEY AUTOINCREMENT,
#     username TEXT UNIQUE,
#     password TEXT
# )
# """)

tool_conn.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

tool_conn.execute("""
CREATE TABLE IF NOT EXISTS threads(
    thread_id TEXT PRIMARY KEY,
    user_id INTEGER,
    title TEXT,
    pdf_name TEXT
)
""")

tool_conn.execute("""
CREATE TABLE IF NOT EXISTS memories(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    memory TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

tool_conn.execute("""
CREATE TABLE IF NOT EXISTS expenses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    category TEXT
)
""")

tool_conn.commit()