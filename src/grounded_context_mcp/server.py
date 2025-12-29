from mcp.server.fastmcp import FastMCP

mcp = FastMCP("grounded-coding-context")

from .tools import search_repo, env_specs, git_insights, grounded_context, recommend_context  # noqa: F401
