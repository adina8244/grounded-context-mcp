from .. import mcp


@mcp.tool()
def env_specs() -> dict:
    """
    Provide environment + operational constraints for coding agents.
    """
    return {
        "server": "grounded-coding-context",
        "scope": "local repo only",
        "network": "disabled/not required",
        "notes": [
            "No GitHub API",
            "Tools return grounded snippets with file paths",
            "Stable schemas enforced via snapshot tests",
        ],
    }
