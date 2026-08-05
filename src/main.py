import asyncio
from dotenv import load_dotenv
load_dotenv()
from src.orchestrator.mcp_client import MCPClientManager
from src.orchestrator.graph import build_workflow
from langchain_core.messages import HumanMessage

async def main():
    # אתחול וחיבור לשרתי ה-MCP
    client_manager = MCPClientManager(config_path="mcp_config.json")
    await client_manager.connect_all()

    try:
        # שליפת כל הכלים שנרשמו משרתי ה-MCP
        mcp_tools = client_manager.get_langchain_tools()
        
        # בניית הגרף
        app = build_workflow(mcp_tools)

        # הרצת שאילתת בדיקה
        query = "תוכל לבדוק את סטטוס ה-Git ולראות אם יש שגיאות בלוגים האחרונים?"
        print(f"\n--- User Query: {query} ---\n")

        inputs = {"messages": [HumanMessage(content=query)]}
        async for chunk in app.astream(inputs, stream_mode="values"):
            latest_message = chunk["messages"][-1]
            latest_message.pretty_print()

    finally:
        await client_manager.close_all()

if __name__ == "__main__":
    asyncio.run(main())