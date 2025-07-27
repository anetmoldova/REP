from typing import List, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from ..models import ChatSession, ChatMessage

# Define the agent's state
class AgentState(TypedDict):
    messages: List[BaseMessage]
    summary: str

llm = ChatOpenAI(temperature=0.5)

# Graph Nodes

def summarization_node(state: AgentState) -> AgentState:
    recent = state["messages"][-5:]
    older = state["messages"][:-5]

    summary = state.get("summary", "")
    if older:
        summary_prompt = [
            HumanMessage(content="Summarize this conversation:"),
            AIMessage(content="\n".join([msg.content for msg in older if isinstance(msg, (HumanMessage, AIMessage))]))
        ]
        response = llm.invoke(summary_prompt)
        summary = response.content

    return {"messages": recent, "summary": summary}

def memory_node(state: AgentState) -> AgentState:
    return state

def llm_node(state: AgentState) -> AgentState:
    prompt = []
    if state.get("summary"):
        prompt.append(HumanMessage(content="Previously on the conversation: " + state["summary"]))
    prompt += state["messages"]
    response = llm.invoke(prompt)
    return {"messages": state["messages"] + [response], "summary": state["summary"]}

# Build LangGraph
def build_agent():
    builder = StateGraph(AgentState)
    builder.add_node("summarize", summarization_node)
    builder.add_node("memory", memory_node)
    builder.add_node("llm", llm_node)
    builder.set_entry_point("summarize")
    builder.add_edge("summarize", "memory")
    builder.add_edge("memory", "llm")
    builder.add_edge("llm", END)
    return builder.compile()

agent = build_agent()

# Load previous chat state from DB
def load_state(session: ChatSession) -> AgentState:
    messages = []
    for msg in session.messages.order_by("timestamp"):
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "ai":
            messages.append(AIMessage(content=msg.content))
    return {"messages": messages, "summary": session.summary or ""}

# Full run function
def run_agent(user_input: str, session: ChatSession) -> List[BaseMessage]:
    # Log user message
    ChatMessage.objects.create(session=session, role="user", content=user_input)

    # Load full conversation state
    state = load_state(session)
    state["messages"].append(HumanMessage(content=user_input))

    # Run LangGraph
    result = agent.invoke(state)

    # Save AI response to DB
    ai_message = result["messages"][-1]
    ChatMessage.objects.create(session=session, role="ai", content=ai_message.content)

    # Save updated summary
    session.summary = result["summary"]
    session.save()

    return result["messages"]
