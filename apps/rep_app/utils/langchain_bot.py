from typing import List, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    messages: List[BaseMessage]

llm = ChatOpenAI(temperature=0.5)

def memory_node(state: AgentState) -> AgentState:
    return state

def llm_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    response = llm.invoke(messages)
    messages.append(response)
    return {"messages": messages}

def build_agent():
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("memory", memory_node)
    graph_builder.add_node("llm", llm_node)
    graph_builder.set_entry_point("memory")
    graph_builder.add_edge("memory", "llm")
    graph_builder.add_edge("llm", END)
    return graph_builder.compile()

agent = build_agent()

def run_agent(user_input: str, session_history: List[BaseMessage] = None) -> List[BaseMessage]:
    if session_history is None:
        session_history = []
    session_history.append(HumanMessage(content=user_input))
    result = agent.invoke({"messages": session_history})
    return result["messages"]