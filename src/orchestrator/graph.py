import os
import logging
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Locate .env file dynamically in the project root directory
project_root = Path(__file__).resolve().parent.parent.parent
env_file = project_root / ".env"
load_dotenv(dotenv_path=env_file)

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from src.orchestrator.state import AgentState

logger = logging.getLogger("OrchestratorGraph")


def build_workflow(mcp_tools: Optional[List[BaseTool]] = None):
    """
    Builds and compiles the LangGraph state graph orchestrator using Groq Llama 3.3.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured in your .env file!")

    # Initialize Groq LLM model with explicit API key loading
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        groq_api_key=api_key
    )

    if mcp_tools:
        llm_with_tools = llm.bind_tools(mcp_tools)
    else:
        llm_with_tools = llm

    def call_agent(state: AgentState):
        messages = state["messages"]
        try:
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        except Exception as exc:
            logger.error(f"LLM Invocation error: {exc}")
            error_text = f"I couldn't process your request because the model failed: {exc}"
            return {"messages": [AIMessage(content=error_text)]}

    # Initialize StateGraph with typed AgentState
    workflow = StateGraph(AgentState)
    
    # Add orchestrator agent node
    workflow.add_node("agent", call_agent)

    # MemorySaver checkpointer persists graph state for Human-in-the-Loop breakpoints
    memory = MemorySaver()

    if mcp_tools:
        # Add ToolNode for executing tools dynamically
        workflow.add_node("tools", ToolNode(mcp_tools))
        
        workflow.set_entry_point("agent")
        
        # Conditional edge: Route to 'tools' node if LLM requests tool execution, otherwise END
        workflow.add_conditional_edges("agent", tools_condition)
        
        # Return flow back to agent after tool execution
        workflow.add_edge("tools", "agent")
        
        # Compile graph with MemorySaver checkpointer and interrupt_before on the "tools" node
        return workflow.compile(
            checkpointer=memory,
            interrupt_before=["tools"]
        )
    else:
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)
        return workflow.compile(checkpointer=memory)