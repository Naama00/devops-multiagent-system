import logging
from dotenv import load_dotenv
import chainlit as cl
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage

from src.orchestrator.mcp_client import MCPClientManager
from src.orchestrator.graph import build_workflow

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChainlitUI")


@cl.on_chat_start
async def on_chat_start():
    """
    Initializes MCP connections and builds the LangGraph workflow when a new chat session starts.
    """
    cl.user_session.set("mcp_manager", None)
    
    # Notify user in the UI about system initialization
    init_msg = cl.Message(content="⚙️ **Initializing DevOps Multi-Agent System & MCP Servers...**")
    await init_msg.send()

    try:
        # Connect to all MCP servers defined in configuration
        client_manager = MCPClientManager(config_path="mcp_config.json")
        await client_manager.connect_all()
        
        # Retrieve tools dynamically from MCP servers
        mcp_tools = client_manager.get_langchain_tools()
        
        # Build LangGraph orchestrator
        app = build_workflow(mcp_tools)
        
        # Store instances in Chainlit session state
        cl.user_session.set("mcp_manager", client_manager)
        cl.user_session.set("graph_app", app)
        cl.user_session.set("thread_id", f"session-{cl.context.session.id}")

        init_msg.content = f"🚀 **DevOps Agent System Ready!** Loaded **{len(mcp_tools)}** MCP tools."
        await init_msg.update()

    except Exception as e:
        logger.error(f"Failed to initialize chat session: {e}", exc_info=True)
        init_msg.content = f"❌ **Initialization Error:** {str(e)}"
        await init_msg.update()


@cl.on_message
async def on_message(message: cl.Message):
    """
    Handles incoming user messages and streams responses from the LangGraph orchestrator.
    """
    app = cl.user_session.get("graph_app")
    thread_id = cl.user_session.get("thread_id")

    if not app:
        await cl.Message(content="⚠️ System is not initialized properly.").send()
        return

    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=message.content)]}

    response_msg = cl.Message(content="")
    await response_msg.send()

    # Stream graph execution steps
    async for chunk in app.astream(inputs, config=config, stream_mode="values"):
        latest_message = chunk["messages"][-1]
        
        if isinstance(latest_message, AIMessage) and latest_message.content:
            response_msg.content = str(latest_message.content)
            await response_msg.update()

    # Check if graph paused at a breakpoint before tool execution
    snapshot = app.get_state(config)
    
    if snapshot.next and "tools" in snapshot.next:
        await handle_human_approval(app, config)


async def handle_human_approval(app, config):
    """
    Displays Human-in-the-Loop interactive approval buttons for pending tool execution calls.
    """
    snapshot = app.get_state(config)
    last_message = snapshot.values["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])

    if not tool_calls:
        return

    # Build human readable summary of requested tool calls
    details = "### 🛑 Human-in-the-Loop Approval Required\n"
    details += "The agent requests permission to execute the following tool(s):\n\n"
    
    for call in tool_calls:
        details += f"* **Tool:** `{call['name']}`\n"
        details += f"  **Arguments:** ```json\n{call['args']}\n```\n"

    # Create interactive action buttons in Chainlit UI
    actions = [
        cl.Action(name="approve_tool", value="approve", label="✅ Approve Execution"),
        cl.Action(name="reject_tool", value="reject", label="❌ Reject Execution")
    ]

    await cl.Message(content=details, actions=actions).send()


@cl.action_callback("approve_tool")
async def on_approve(action: cl.Action):
    """
    Callback triggered when human operator approves tool execution.
    """
    await action.remove()
    app = cl.user_session.get("graph_app")
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}}

    msg = cl.Message(content="✅ **Execution Approved.** Executing tool(s)...")
    await msg.send()

    # Resume graph execution passing None to proceed past breakpoint
    async for chunk in app.astream(None, config=config, stream_mode="values"):
        latest_message = chunk["messages"][-1]
        if isinstance(latest_message, AIMessage) and latest_message.content:
            msg.content = str(latest_message.content)
            await msg.update()

    # Check for any subsequent tool calls
    snapshot = app.get_state(config)
    if snapshot.next and "tools" in snapshot.next:
        await handle_human_approval(app, config)


@cl.action_callback("reject_tool")
async def on_reject(action: cl.Action):
    """
    Callback triggered when human operator rejects tool execution.
    """
    await action.remove()
    app = cl.user_session.get("graph_app")
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}}

    snapshot = app.get_state(config)
    last_message = snapshot.values["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])

    # Synthesize rejection messages
    rejection_messages = [
        ToolMessage(
            content=f"Tool execution '{call['name']}' was rejected by human operator.",
            tool_call_id=call["id"]
        ) for call in tool_calls
    ]

    # Inject rejection into graph state
    app.update_state(config, {"messages": rejection_messages}, as_node="tools")

    msg = cl.Message(content="❌ **Execution Rejected.** Notifying agent...")
    await msg.send()

    # Resume graph to let LLM acknowledge cancellation
    async for chunk in app.astream(None, config=config, stream_mode="values"):
        latest_message = chunk["messages"][-1]
        if isinstance(latest_message, AIMessage) and latest_message.content:
            msg.content = str(latest_message.content)
            await msg.update()


@cl.on_chat_end
async def on_chat_end():
    """
    Cleans up MCP connections gracefully when the chat session closes.
    """
    client_manager = cl.user_session.get("mcp_manager")
    if client_manager:
        logger.info("Closing MCP sessions for session end...")
        await client_manager.close_all()