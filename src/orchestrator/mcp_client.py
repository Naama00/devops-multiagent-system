import json
import logging
from pathlib import Path
from contextlib import AsyncExitStack
from typing import List, Dict, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_core.tools import StructuredTool
from pydantic import create_model, Field

logger = logging.getLogger("MCPClientManager")


def _json_schema_to_pydantic(schema: Dict[str, Any]) -> type:
    """
    Dynamically converts an MCP JSON Schema properties map into a Pydantic model for LangChain.
    """
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    
    fields = {}
    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict
    }
    
    for prop_name, prop_info in properties.items():
        json_type = prop_info.get("type", "string")
        py_type = type_mapping.get(json_type, Any)
        description = prop_info.get("description", "")
        
        if prop_name in required_fields:
            fields[prop_name] = (py_type, Field(..., description=description))
        else:
            default_val = prop_info.get("default", None)
            fields[prop_name] = (py_type, Field(default_val, description=description))

    return create_model("DynamicToolSchema", **fields)


class MCPClientManager:
    """
    Manages connections to multiple MCP servers and converts their tools into LangChain tools.
    """
    def __init__(self, config_path: str = "mcp_config.json"):
        self.config_path = config_path
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, ClientSession] = {}
        self.langchain_tools: List[StructuredTool] = []

    async def connect_all(self):
        """
        Connects to all configured MCP stdio servers and initializes their sessions.
        """
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        mcp_servers = config.get("mcpServers", {})

        for server_name, server_info in mcp_servers.items():
            try:
                logger.info(f"Connecting to MCP Server: {server_name}")
                server_params = StdioServerParameters(
                    command=server_info["command"],
                    args=server_info["args"],
                    env=server_info.get("env")
                )

                # Connect stdio transport safely using AsyncExitStack
                read_stream, write_stream = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )

                # Create and initialize ClientSession
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                await session.initialize()
                self.sessions[server_name] = session
                
                # Fetch available tools from the MCP server
                tools_response = await session.list_tools()
                for tool in tools_response.tools:
                    lc_tool = self._convert_mcp_to_langchain_tool(session, tool)
                    self.langchain_tools.append(lc_tool)

                logger.info(f"Successfully connected to {server_name}. Loaded {len(tools_response.tools)} tool(s).")

            except Exception as e:
                logger.error(f"Failed to connect to MCP server '{server_name}': {e}")

    def _convert_mcp_to_langchain_tool(self, session: ClientSession, tool: Any) -> StructuredTool:
        """
        Converts an individual MCP tool schema into a LangChain StructuredTool.
        """
        tool_name = tool.name
        tool_description = tool.description or ""
        input_schema = tool.inputSchema or {}

        # Build dynamic args schema using Pydantic
        args_schema = _json_schema_to_pydantic(input_schema)

        async def _coroutine(**kwargs) -> str:
            try:
                result = await session.call_tool(tool_name, arguments=kwargs)
                # Parse text response from content list
                text_outputs = [content.text for content in result.content if hasattr(content, "text")]
                return "\n".join(text_outputs) if text_outputs else "Tool executed successfully."
            except Exception as exc:
                return f"Error executing tool '{tool_name}': {str(exc)}"

        return StructuredTool.from_function(
            coroutine=_coroutine,
            name=tool_name,
            description=tool_description,
            args_schema=args_schema
        )

    def get_langchain_tools(self) -> List[StructuredTool]:
        """
        Returns the list of registered LangChain tools acquired from MCP servers.
        """
        return self.langchain_tools

    async def close_all(self):
        """
        Gracefully closes all active sessions and exits the context stack.
        """
        logger.info("Closing all MCP server sessions...")
        await self.exit_stack.aclose()
        self.sessions.clear()
        self.langchain_tools.clear()