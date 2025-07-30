from typing import List, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
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
llm = ChatOpenAI(temperature=0, api_key=OPENAI_API_KEY)

# === SQL DB SETUP ===
connection_uri = f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
db = SQLDatabase.from_uri(
    connection_uri,
    include_tables=["metrics_vals", "geo_location"],
    sample_rows_in_table_info=2
)

# === SQL Agent (direct call version) ===
agent_executor = create_sql_agent(
    llm=llm,
    db=db,
    agent_type="openai-tools",
    verbose=True
)

def ask_agent(question: str) -> str:
    """Direct access to SQL agent."""
    return agent_executor.run(question)

# === Tools for routing ===
tools = [
    Tool(
        name="Real Estate DB",
        func=lambda q: agent_executor.run(q),
        description=(
            "ONLY use this tool for questions that clearly ask about real estate data, pricing, metrics, or "
            "values from a database. DO NOT use this for personal, general, or unrelated questions."
        )
    ),
    Tool(
        name="General Chat",
        func=lambda q: llm.invoke(q).content,
        description=(
            "Use this tool for anything that is NOT about structured real estate data — such as personal greetings, "
            "questions about names, languages, emotions, etc."
        )
    )
]

tool_agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent_type="openai-tools",
    verbose=True,
    agent_kwargs={
        "system_message": (
            "You are a smart assistant. Your job is to choose between tools carefully:\n"
            "- Only use the 'Real Estate DB' tool if the user is asking for data stored in the database "
            "(like prices, regions, or metrics).\n"
            "- For greetings, personal questions, or general topics, use 'General Chat'."
        )
    }
)


# === LangGraph State ===
class AgentState(TypedDict):
    messages: List[BaseMessage]
    summary: str

# === Nodes ===
def summarization_node(state: AgentState) -> AgentState:
    if len(state["messages"]) < 5:
        return state

    recent = state["messages"][-5:]
    older = state["messages"][:-5]
    summary = state.get("summary", "")

    if older:
        history = "\n".join(
            msg.content for msg in older if isinstance(msg, (HumanMessage, AIMessage))
        )
        prompt = f"Summarize this conversation:\n{history}"
        summary = llm.invoke(prompt).content

    return {"messages": recent, "summary": summary}

def memory_node(state: AgentState) -> AgentState:
    return state

def agent_node(state: AgentState) -> AgentState:
    context = state.get("summary", "")
    question = state["messages"][-1].content
    prompt = f"Previously on the conversation:\n{context}\n\n{question}" if context else question
    response = tool_agent.run(prompt)
    return {"messages": state["messages"] + [AIMessage(content=response)], "summary": state["summary"]}

# === Build LangGraph ===
def build_agent():
    builder = StateGraph(AgentState)
    builder.add_node("summarize", RunnableLambda(summarization_node))
    builder.add_node("memory", RunnableLambda(memory_node))
    builder.add_node("agent", RunnableLambda(agent_node))

    builder.set_entry_point("summarize")
    builder.add_edge("summarize", "memory")
    builder.add_edge("memory", "agent")
    builder.add_edge("agent", END)

    return builder.compile()

agent = build_agent()

# === Load Messages from DB ===
def load_state(session: ChatSession) -> AgentState:
    messages = []
    for msg in session.messages.order_by("timestamp"):
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "ai":
            messages.append(AIMessage(content=msg.content))
    return {"messages": messages, "summary": session.summary or ""}

# === Main LangGraph Entry ===
def run_agent(user_input: str, session: ChatSession) -> List[BaseMessage]:
    ChatMessage.objects.create(session=session, role="user", content=user_input)

    state = load_state(session)
    state["messages"].append(HumanMessage(content=user_input))

    result = agent.invoke(state)

    ai_response = result["messages"][-1]
    ChatMessage.objects.create(session=session, role="ai", content=ai_response.content)

    session.summary = result["summary"]
    session.save()

    return result["messages"]
