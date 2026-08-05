import subprocess
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("InfraServer")

ALLOWED_COMMANDS = ["ls", "dir", "git", "echo", "pwd"]

@mcp.tool()
def execute_safe_command(command: str, args: list[str] = None) -> str:
    """
    Executes a safe shell command on the host.
    
    Args:
        command: The command to run (e.g., 'dir', 'git', 'echo').
        args: Optional list of arguments for the command.
    """
    if args is None:
        args = []

    if command not in ALLOWED_COMMANDS:
        return f"Error: Command '{command}' is not in the allowed list: {ALLOWED_COMMANDS}"

    try:
        full_cmd = [command] + args
        result = subprocess.run(
            full_cmd, 
            capture_output=True, 
            text=True, 
            timeout=10,
            shell=True
        )
        
        if result.returncode == 0:
            return result.stdout if result.stdout else "Command executed successfully with no output."
        else:
            return f"Command failed with error:\n{result.stderr}"
            
    except Exception as e:
        return f"Execution exception: {str(e)}"

if __name__ == "__main__":
    mcp.run()