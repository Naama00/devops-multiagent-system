import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

from src.orchestrator.mcp_client import MCPClientManager
from src.orchestrator.graph import build_workflow
from langchain_core.messages import HumanMessage, ToolMessage

# Configure application logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MainApp")


async def run_interactive_workflow(app, user_query: str, thread_id: str = "thread-1"):
    """
    Runs the graph workflow interactively with Human-in-the-Loop tool approval.
    """
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=user_query)]}

    print(f"\n================ User Query ================\n{user_query}\n============================================\n")

    # Run initial workflow stream until completion or breakpoint
    try:
        async for chunk in app.astream(inputs, config=config, stream_mode="values"):
            latest_message = chunk["messages"][-1]
            latest_message.pretty_print()
    except Exception as exc:
        logger.error(f"Workflow stream failed: {exc}", exc_info=True)
        print(f"\nThe workflow could not complete: {exc}\n")
        return

    # Check if graph paused at a breakpoint before executing tools
    snapshot = app.get_state(config)
    
    while snapshot.next and "tools" in snapshot.next:
        last_message = snapshot.values["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", [])

        if not tool_calls:
            break

        print("\n" + "=" * 55)
        print("🛑 HUMAN-IN-THE-LOOP APPROVAL REQUIRED 🛑")
        print("=" * 55)
        for i, call in enumerate(tool_calls, 1):
            print(f"[{i}] Tool Requested : {call['name']}")
            print(f"    Arguments      : {call['args']}")
        print("=" * 55)

        # Get interactive human input from terminal
        user_approval = input("\nDo you approve executing these tool(s)? (y/n): ").strip().lower()

        if user_approval in ["y", "yes"]:
            print("\n✅ Execution APPROVED by human operator. Resuming workflow...\n")
            # Resume graph execution by passing None to continue from checkpoint
            async for chunk in app.astream(None, config=config, stream_mode="values"):
                latest_message = chunk["messages"][-1]
                latest_message.pretty_print()
        else:
            print("\n❌ Execution REJECTED by human operator. Notifying agent...\n")
            # Create rejection messages for each requested tool
            rejection_messages = [
                ToolMessage(
                    content=f"Tool execution '{call['name']}' was rejected by human operator.",
                    tool_call_id=call["id"]
                ) for call in tool_calls
            ]
            # Inject rejection messages into state as if tool node completed with error
            app.update_state(config, {"messages": rejection_messages}, as_node="tools")
            
            # Resume workflow to allow LLM to handle cancellation gracefully
            async for chunk in app.astream(None, config=config, stream_mode="values"):
                latest_message = chunk["messages"][-1]
                latest_message.pretty_print()

        # Refresh state snapshot for any subsequent tool calls
        snapshot = app.get_state(config)


async def main():
    logger.info("Initializing MCP Client Manager...")
    client_manager = MCPClientManager(config_path="mcp_config.json")
    
    try:
        # Connect to all registered MCP servers
        await client_manager.connect_all()
        
        # Retrieve registered tools
        mcp_tools = client_manager.get_langchain_tools()
        logger.info(f"Total tools loaded into LangGraph: {len(mcp_tools)}")

        # Build workflow with HITL support
        app = build_workflow(mcp_tools)

        # Sample query that triggers a tool execution (e.g. Git branch creation)
        query = "תוכל ליצור ענף חדש בשם feature/hitl-test ב-Git?"
        
        await run_interactive_workflow(app, query, thread_id="devops-session-1")

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        print(f"\nStartup failed: {e}\n")
    finally:
        logger.info("Cleaning up MCP resources...")
        await client_manager.close_all()


if __name__ == "__main__":
    asyncio.run(main())