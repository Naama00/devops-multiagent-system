import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

from src.orchestrator.mcp_client import MCPClientManager
from src.orchestrator.graph import build_workflow
from langchain_core.messages import HumanMessage

# Configure application logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MainApp")


async def main():
    logger.info("Initializing MCP Client Manager...")
    client_manager = MCPClientManager(config_path="mcp_config.json")
    
    try:
        # Connect to all MCP servers listed in mcp_config.json
        await client_manager.connect_all()
        
        # Retrieve dynamically registered tools
        mcp_tools = client_manager.get_langchain_tools()
        logger.info(f"Total tools loaded into LangGraph: {len(mcp_tools)}")

        # Construct compiled LangGraph workflow
        app = build_workflow(mcp_tools)

        # Execute sample user query
        query = "תוכל לבדוק את סטטוס ה-Git ולראות אם יש שגיאות בלוגים האחרונים?"
        print(f"\n--- User Query: {query} ---\n")

        inputs = {"messages": [HumanMessage(content=query)]}
        
        # Stream workflow execution outputs step-by-step
        async for chunk in app.astream(inputs, stream_mode="values"):
            latest_message = chunk["messages"][-1]
            latest_message.pretty_print()

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up resources...")
        await client_manager.close_all()


if __name__ == "__main__":
    asyncio.run(main())