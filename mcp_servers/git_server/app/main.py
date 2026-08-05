import subprocess
import logging
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GitMCPServer")

# Initialize FastMCP server
mcp = FastMCP("GitServer")

@mcp.tool()
async def get_git_status(repo_path: str = ".") -> str:
    """
    Returns the current git status of the specified repository path.
    """
    logger.info(f"Checking git status for repository at: {repo_path}")
    try:
        result = subprocess.run(
            ["git", "status"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout
        return f"Git status error: {result.stderr}"
    except Exception as e:
        return f"Execution error: {str(e)}"

@mcp.tool()
async def get_git_diff(repo_path: str = ".") -> str:
    """
    Returns the uncommitted git diffs of the repository.
    """
    logger.info(f"Fetching git diff for repository at: {repo_path}")
    try:
        result = subprocess.run(
            ["git", "diff"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout if result.stdout else "No uncommitted changes found."
        return f"Git diff error: {result.stderr}"
    except Exception as e:
        return f"Execution error: {str(e)}"

@mcp.tool()
async def create_git_branch(branch_name: str, repo_path: str = ".") -> str:
    """
    Creates and switches to a new git branch.
    """
    logger.info(f"Creating new branch '{branch_name}' at: {repo_path}")
    try:
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return f"Successfully created and switched to branch '{branch_name}'."
        return f"Git branch error: {result.stderr}"
    except Exception as e:
        return f"Execution error: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting Git MCP Server on stdio transport...")
    mcp.run(transport="stdio")