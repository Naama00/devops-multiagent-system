import subprocess
import logging
from typing import List, Optional
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InfraMCPServer")

# Initialize FastMCP server
mcp = FastMCP("InfraServer")

ALLOWED_COMMANDS = {"ls", "dir", "git", "echo", "pwd"}

@mcp.tool()
def execute_safe_command(command: str, args: Optional[List[str]] = None) -> str:
    """
    Executes a safe shell command on the host securely without shell=True.
    
    Args:
        command: The command to run (e.g., 'dir', 'git', 'echo').
        args: Optional list of arguments for the command.
    """
    if args is None:
        args = []

    clean_command = command.strip()
    if clean_command not in ALLOWED_COMMANDS:
        return f"Error: Command '{clean_command}' is not in the allowed list: {sorted(list(ALLOWED_COMMANDS))}"

    try:
        # Build command array safely (shell=False prevents command injection vulnerabilities)
        full_cmd = [clean_command] + args
        logger.info(f"Executing command safely: {full_cmd}")
        
        result = subprocess.run(
            full_cmd, 
            capture_output=True, 
            text=True, 
            timeout=15,
            shell=False
        )
        
        if result.returncode == 0:
            return result.stdout if result.stdout else "Command executed successfully with no output."
        else:
            return f"Command failed (exit code {result.returncode}):\n{result.stderr}"
            
    except FileNotFoundError:
        return f"Execution error: Command '{clean_command}' not found on host system."
    except Exception as e:
        logger.error(f"Execution exception: {str(e)}")
        return f"Execution exception: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting Infrastructure MCP Server on stdio transport...")
    mcp.run()