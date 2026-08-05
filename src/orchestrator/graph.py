import os
import httpx
import logging
from typing import List, Optional

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition

from src.orchestrator.state import AgentState

logger = logging.getLogger("OrchestratorGraph")

# Safely configure SSL certificate path if CA file exists
CA_CERT_PATH = "netfree-ca.crt"
if os.path.exists(CA_CERT_PATH):
    os.environ["SSL_CERT_FILE"] = CA_CERT_PATH
    os.environ["REQUESTS_CA_BUNDLE"] = CA_CERT_PATH
    logger.info(f"Configured custom SSL CA certificate from {CA_CERT_PATH}")
else:
    # Fallback monkey-patch only for environments requiring SSL bypass
    _original_init = httpx.Client.__init__
    def _patched_init(self, *args, **kwargs):
        kwargs["verify"] = False
        _original_init(self, *args, **kwargs)
    httpx.Client.__init__ = _patched_init


def build_workflow(mcp_tools: Optional[List[BaseTool]] = None):
    """
    Builds and compiles the LangGraph state graph orchestrator.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
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

    if mcp_tools:
        # Add ToolNode for executing tool calls dynamically
        workflow.add_node("tools", ToolNode(mcp_tools))
        
        workflow.set_entry_point("agent")
        
        # Conditional edge: Route to 'tools' node if LLM requests tool execution, otherwise END
        workflow.add_conditional_edges("agent", tools_condition)
        
        # Return flow back to agent after tool execution
        workflow.add_edge("tools", "agent")
    else:
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)

    return workflow.compile()