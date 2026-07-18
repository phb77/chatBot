

# import streamlit as st
# from database import tool_conn


# # ============================================================
# # AUTH PAGE
# # ============================================================

# def auth_page():

#     # Page title
#     st.title("Welcome to LangGraph ChatBot")

#     # Login / Signup selector
#     option = st.radio(
#         "Account",
#         ["Login", "Sign Up"],
#         horizontal=True,
#         label_visibility="collapsed"
#     )

#     # ---------------- LOGIN ----------------

#     if option == "Login":

#         st.subheader("Enter your login credentials")

#         username = st.text_input(
#             "Username:",
#             placeholder="Enter your Username",
#             key="login_username"
#         )

#         password = st.text_input(
#             "Password:",
#             placeholder="Enter your Password",
#             type="password",
#             key="login_password"
#         )

#         submit = st.button(
#             "Login",
#             use_container_width=True,
#             type="primary"
#         )

#         return "login", username, password, submit


#     # ---------------- SIGN UP ----------------

#     else:

#         st.subheader("Create your account")

#         username = st.text_input(
#             "Username:",
#             placeholder="Enter your Username",
#             key="signup_username"
#         )

#         password = st.text_input(
#             "Password:",
#             placeholder="Enter your Password",
#             type="password",
#             key="signup_password"
#         )

#         submit = st.button(
#             "Create Account",
#             use_container_width=True,
#             type="primary"
#         )

#         return "signup", username, password, submit


# # ============================================================
# # DATABASE
# # ============================================================

# def register_user(username, password):

#     cursor = tool_conn.execute(
#         """
#         SELECT *
#         FROM users
#         WHERE username=?
#         """,
#         (username,)
#     )

#     if cursor.fetchone():

#         return False, "Username already exists."

#     tool_conn.execute(
#         """
#         INSERT INTO users(
#             username,
#             password
#         )
#         VALUES(?,?)
#         """,
#         (
#             username,
#             password
#         )
#     )

#     tool_conn.commit()

#     return True, "Registration successful. Please login."


# def login_user(username, password):

#     cursor = tool_conn.execute(
#         """
#         SELECT user_id
#         FROM users
#         WHERE username=?
#         AND password=?
#         """,
#         (
#             username,
#             password
#         )
#     )

#     row = cursor.fetchone()

#     if row is None:

#         return None

#     return row[0]



import re
import streamlit as st
from database import tool_conn


# ============================================================
# AUTH PAGE
# ============================================================

def auth_page():

    st.title("Welcome to LangGraph ChatBot")

    option = st.radio(
        "Account",
        ["Login", "Sign Up"],
        horizontal=True,
        label_visibility="collapsed"
    )

    # ---------------- LOGIN ----------------

    if option == "Login":

        st.subheader("Enter your login credentials")

        email = st.text_input(
            "Email",
            placeholder="Enter your Email",
            key="login_email"
        )

        password = st.text_input(
            "Password",
            placeholder="Enter your Password",
            type="password",
            key="login_password"
        )

        submit = st.button(
            "Login",
            use_container_width=True,
            type="primary"
        )

        return "login", email, password, submit

    # ---------------- SIGN UP ----------------

    else:

        st.subheader("Create your account")

        email = st.text_input(
            "Email",
            placeholder="Enter your Email",
            key="signup_email"
        )

        password = st.text_input(
            "Password",
            placeholder="Create your Password",
            type="password",
            key="signup_password"
        )

        submit = st.button(
            "Create Account",
            use_container_width=True,
            type="primary"
        )

        return "signup", email, password, submit


# ============================================================
# EMAIL VALIDATION
# ============================================================

def valid_email(email: str) -> bool:
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, email) is not None


# ============================================================
# REGISTER USER
# ============================================================

def register_user(email, password):

    email = email.strip().lower()

    if not valid_email(email):
        return False, "Please enter a valid email address."

    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    cursor = tool_conn.execute(
        """
        SELECT *
        FROM users
        WHERE email=?
        """,
        (email,)
    )

    if cursor.fetchone():
        return False, "Email already registered."

    tool_conn.execute(
        """
        INSERT INTO users(
            email,
            password
        )
        VALUES(?,?)
        """,
        (
            email,
            password
        )
    )

    tool_conn.commit()

    return True, "Registration successful. Please login."


# ============================================================
# LOGIN USER
# ============================================================

def login_user(email, password):

    email = email.strip().lower()

    cursor = tool_conn.execute(
        """
        SELECT user_id
        FROM users
        WHERE email=?
        AND password=?
        """,
        (
            email,
            password
        )
    )

    row = cursor.fetchone()

    if row is None:
        return None

    return row[0]