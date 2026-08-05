import os
import logging
from typing import List
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ObservabilityMCPServer")

# Initialize FastMCP server
mcp = FastMCP("ObservabilityServer")

@mcp.tool()
async def read_recent_logs(log_file_path: str, lines_count: int = 50) -> str:
    """
    Reads the last N lines from a specified log file.
    """
    logger.info(f"Reading last {lines_count} lines from log file: {log_file_path}")
    if not os.path.exists(log_file_path):
        return f"Error: Log file not found at path '{log_file_path}'"

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            recent_lines = lines[-lines_count:] if len(lines) >= lines_count else lines
            return "".join(recent_lines)
    except Exception as e:
        return f"Error reading log file: {str(e)}"

@mcp.tool()
async def filter_error_logs(log_file_path: str, keywords: List[str] = None) -> str:
    """
    Filters log file entries containing 'ERROR', 'CRITICAL', 'EXCEPTION', or specified custom keywords.
    """
    if keywords is None:
        keywords = ["ERROR", "CRITICAL", "EXCEPTION", "FAIL"]

    logger.info(f"Filtering error logs from {log_file_path} using keywords: {keywords}")
    if not os.path.exists(log_file_path):
        return f"Error: Log file not found at path '{log_file_path}'"

    try:
        matched_lines = []
        with open(log_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if any(keyword.lower() in line.lower() for keyword in keywords):
                    matched_lines.append(line)

        if not matched_lines:
            return "No matching error entries found in the log file."
        return "".join(matched_lines[-100:])  # Return up to last 100 error matches
    except Exception as e:
        return f"Error filtering log file: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting Observability MCP Server on stdio transport...")
    mcp.run(transport="stdio")