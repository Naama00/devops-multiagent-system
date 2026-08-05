import httpx
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from src.orchestrator.state import AgentState

# עקיפת אימות SSL גלובלית ב-httpx עבור Google GenAI SDK
_original_init = httpx.Client.__init__

def _patched_init(self, *args, **kwargs):
    kwargs["verify"] = False
    _original_init(self, *args, **kwargs)

httpx.Client.__init__ = _patched_init

def build_workflow(mcp_tools):
    # שימוש בשם המודל הרשמי והמעודכן
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0
    )
    
    if mcp_tools:
        llm_with_tools = llm.bind_tools(mcp_tools)
    else:
        llm_with_tools = llm

    def call_agent(state: AgentState):
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_agent)
    
    if mcp_tools:
        workflow.add_node("tools", ToolNode(mcp_tools))

    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)

    return workflow.compile()

    # התניה לניתוב: האם יש צורך בהפעלת כלי או סיום
    def should_continue(state: AgentState):
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # יצירת הגרף והוספת הצמתים
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_agent)
    workflow.add_node("tools", ToolNode(mcp_tools))

    # הגדרת נקודת ההתחלה והקשתות
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")

    return workflow.compile()