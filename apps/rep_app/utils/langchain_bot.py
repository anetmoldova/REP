from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.agents import Tool, initialize_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from ..models import ChatSession, ChatMessage
import os

# === ENV CONFIG ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PG_USER = os.getenv("POSTGRES_USER", "vanhieuvu")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "nanuk§2")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "4321")
PG_DB = os.getenv("POSTGRES_DB", "rep_db")

# === LLM ===
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not set")
    llm = None
else:
    try:
        llm = ChatOpenAI(temperature=0, api_key=OPENAI_API_KEY)
        print("✅ LLM initialized successfully")
    except Exception as e:
        print(f"Failed to initialize LLM: {e}")
        llm = None

# === SQL DB SETUP ===
try:
    connection_uri = f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    db = SQLDatabase.from_uri(
        connection_uri,
        include_tables=["metrics_vals", "geo_location"],
        sample_rows_in_table_info=2
    )
    print("✅ SQL Database connected successfully")
except Exception as e:
    print(f"Failed to connect to SQL database: {e}")
    db = None

# === SQL Agent (direct call version) ===
if llm and db:
    try:
        agent_executor = create_sql_agent(
            llm=llm,
            db=db,
            agent_type="openai-tools",
            verbose=True
        )
        print("✅ SQL Agent created successfully")
    except Exception as e:
        print(f"Failed to create SQL agent: {e}")
        agent_executor = None
else:
    agent_executor = None

def ask_agent(question: str) -> str:
    """Direct access to SQL agent."""
    if tool_agent:
        return tool_agent.run(question)
    else:
        return "SQL agent not available"

# === Tools for routing ===
if llm and agent_executor:
    tools = [
        Tool(
            name="Real Estate DB",
            func=lambda q: agent_executor.run(q),
            description="Use ONLY when the question is about specific real estate metrics stored in a database (e.g. price, area, location, values). NEVER use for greetings, general conversation, or casual questions."
        ),
        Tool(
            name="General Chat",
            func=lambda q: llm.invoke(q).content,
            description="Use ONLY for friendly chat, greetings, emotional support, or any question NOT asking for a number or real estate metric."
        )
    ]

    tool_agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent_type="zero-shot-react-description",
        verbose=True,
        agent_kwargs={
            "system_message": (
                "You are a smart assistant with access to two tools:\n"
                "- If the user asks about real estate metrics (like monthly price, area, region), use the 'Real Estate DB' tool.\n"
                "- If the user is greeting you, making small talk, or asking a personal/non-technical question, use 'General Chat'.\n"
                "NEVER use the Real Estate DB tool for small talk or greetings."
            )
        }
    )
    print("✅ Tool agent initialized successfully")
else:
    tool_agent = None
    print("❌ Tool agent not available - missing LLM or SQL agent")

# === Simple agent function for views.py ===
def get_agent_response(user_input: str, session: ChatSession = None) -> str:
    """Get response from the agent with session context"""
    if not tool_agent:
        return "I'm sorry, but I'm not able to access my tools right now."
    
    try:
        # If we have session context, include recent messages
        if session:
            # Get recent messages safely without negative indexing
            all_messages = list(session.messages.order_by('timestamp'))
            if len(all_messages) > 0:
                # Get last 3 messages safely
                recent_messages = all_messages[-3:] if len(all_messages) >= 3 else all_messages
                context = "\n".join([
                    f"User: {m.content}" if m.is_user else f"Assistant: {m.content}"
                    for m in recent_messages
                ]) + f"\nUser: {user_input}"
                return tool_agent.run(context)
        
        # Otherwise just use the direct input
        return tool_agent.run(user_input)
    except Exception as e:
        print(f"Agent error: {e}")
        return f"I'm having trouble processing your request. Please try again. (Error: {str(e)})"