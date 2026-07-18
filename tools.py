import json
from database import tool_conn
from langchain_core.tools import tool
import requests
import yfinance as yf
from langchain_tavily import TavilySearch
from langchain_community.tools import DuckDuckGoSearchRun
from dotenv import load_dotenv
from rag import get_retriever, vectorstore_exists
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
import os
 
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

#google search
search = TavilySearch(
    max_results=5,
    topic="news",
    include_answer=True,
    include_raw_content=True
)

@tool
def web_search(query: str) -> str:
    """
    Search the internet for the latest information.
    """

    result = search.invoke({"query": query})

    if not result.get("results"):
        return "No results found."

    output = []

    for i, item in enumerate(result["results"], 1):

        output.append(
            f"""
Title: {item.get("title")}

Content: {item.get("content")}

URL: {item.get("url")}

Published: {item.get("published_date","Unknown")}
"""
        )

    return "\n\n".join(output)

#calculator
@tool
def calculator(expression: str) -> dict:
    """
    Evaluate a mathematical expression.

    Examples:
    2+5
    (10+20)*5
    100/4
    2^10
    """

    try:

        url = "https://api.mathjs.org/v4/"

        response = requests.get(
            url,
            params={
                "expr": expression
            }
        )

        if response.status_code == 200:

            return {
                "status": "success",
                "expression": expression,
                "result": response.text
            }

        return {
            "status": "error",
            "message": "Unable to calculate."
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


#add expanse 
@tool
def add_expense(
    amount: float,
    category: str,
    config: RunnableConfig
) -> dict:
    """
    Add expense.

    If the category already exists,
    its amount is increased.
    """

    try:

        user_id = config["configurable"]["user_id"]

        cursor = tool_conn.execute(
            """
            SELECT amount
            FROM expenses
            WHERE user_id=?
            AND LOWER(category)=LOWER(?)
            """,
            (user_id, category)
        )

        row = cursor.fetchone()

        if row:

            total_amount = row[0] + amount

            tool_conn.execute(
                """
                UPDATE expenses
                SET amount=?
                WHERE user_id=?
                AND LOWER(category)=LOWER(?)
                """,
                (
                    total_amount,
                    user_id,
                    category
                )
            )

        else:

            tool_conn.execute(
                """
                INSERT INTO expenses(
                    user_id,
                    amount,
                    category
                )
                VALUES(?,?,?)
                """,
                (
                    user_id,
                    amount,
                    category
                )
            )

            total_amount = amount

        tool_conn.commit()

        return {
            "status": "success",
            "message": "Expense added successfully.",
            "total_amount": total_amount
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


#Show Expenses
@tool
def show_expenses(
    config: RunnableConfig
) -> dict:
    """
    Show all expenses.
    """

    try:

        user_id = config["configurable"]["user_id"]

        cursor = tool_conn.execute(
            """
            SELECT
            id,
            amount,
            category
            FROM expenses
            WHERE user_id=?
            """,
            (user_id,)
        )

        rows = cursor.fetchall()

        total = 0

        expenses = []

        for row in rows:

            expenses.append(
                {
                    "id": row[0],
                    "amount": row[1],
                    "category": row[2]
                }
            )

            total += row[1]

        return {
            "total": total,
            "expenses": expenses
        }

    except Exception as e:

        return {
            "error": str(e)
        }


#delete expence 
@tool
def delete_expense(
    category: str,
    config: RunnableConfig
) -> dict:
    """
    Delete an expense using its category.
    """

    try:

        user_id = config["configurable"]["user_id"]

        cursor = tool_conn.execute(
            """
            SELECT
            id,
            amount
            FROM expenses
            WHERE user_id=?
            AND LOWER(category)=LOWER(?)
            ORDER BY id
            LIMIT 1
            """,
            (
                user_id,
                category
            )
        )

        row = cursor.fetchone()

        if row is None:

            return {
                "status": "error",
                "message": f"No expense found for '{category}'."
            }

        expense_id = row[0]

        amount = row[1]

        tool_conn.execute(
            """
            DELETE FROM expenses
            WHERE id=?
            AND user_id=?
            """,
            (
                expense_id,
                user_id
            )
        )

        tool_conn.commit()

        return {
            "status": "success",
            "deleted_id": expense_id,
            "amount": amount,
            "category": category,
            "message": "Expense deleted successfully."
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }

#stock price 
@tool
def get_stock_price(symbol: str) -> dict:
    """
    Get current stock price.

    Examples:
    AAPL
    TSLA
    IRCTC
    RELIANCE
    TCS
    """

    try:
        # ---------- Try Alpha Vantage ----------
        url = (
            "https://www.alphavantage.co/query"
            f"?function=GLOBAL_QUOTE"
            f"&symbol={symbol}"
            f"&apikey=NQ128RSHCRK3G0GQ"
        )

        response = requests.get(url).json()

        quote = response.get("Global Quote", {})

        if quote and quote.get("05. price"):

            return {
                "source": "Alpha Vantage",
                "symbol": quote.get("01. symbol"),
                "price": quote.get("05. price")
            }

    except Exception:
        pass

    # ---------- Fallback to Yahoo Finance ----------
    try:

        yahoo_symbol = symbol

        # Add .NS only if user didn't provide an exchange suffix
        if "." not in yahoo_symbol:
            yahoo_symbol += ".NS"

        stock = yf.Ticker(yahoo_symbol)

        price = stock.fast_info.get("lastPrice")

        if price is None:
            return {
                "error": "Unable to fetch stock price."
            }

        return {
            "source": "Yahoo Finance",
            "symbol": yahoo_symbol,
            "price": price
        }

    except Exception as e:

        return {
            "error": str(e)
        }


@tool
def pdf_search(
    question: str,
    config: RunnableConfig
) -> str:
    """
        Search the uploaded PDF for information.

        Always use this tool whenever the user asks about the
        uploaded PDF, including:
        - summarize the PDF
        - summary of the PDF
        - explain the PDF
        - answer questions from the PDF
        - retrieve information from the uploaded document

        The PDF is already uploaded for the current conversation.
        Do not ask the user to upload it again.
    """

    try:
        print("PDF TOOL CONFIG:", config)

        user_id = config["configurable"]["user_id"]
        thread_id = config["configurable"]["thread_id"]

        print("USER ID:", user_id)
        print("THREAD ID:", thread_id)

        print(
            "VECTORSTORE EXISTS:",
            vectorstore_exists(user_id, thread_id)
        )

        if not vectorstore_exists(user_id, thread_id):
            return "No PDF has been uploaded for this conversation."

        retriever = get_retriever(
            user_id,
            thread_id
        )

        docs = retriever.invoke(question)

        if not docs:
            return "No relevant information found in the PDF."

        return "\n\n".join(
            doc.page_content
            for doc in docs
        )

    except Exception as e:
        print("PDF SEARCH ERROR:", repr(e))
        return f"PDF search failed: {str(e)}"

tools = [
    web_search,
    calculator,
    add_expense,
    show_expenses,
    delete_expense,
    get_stock_price,
    pdf_search
    ]

