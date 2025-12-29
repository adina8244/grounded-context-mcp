import json
import inspect
from pathlib import Path

import anyio

from grounded_context_mcp.server import mcp

SNAP = Path(__file__).parent / "snapshots" / "tools_schema.json"


def _normalize(obj):
    if isinstance(obj, dict):
        return {k: _normalize(obj[k]) for k in sorted(obj)}
    if isinstance(obj, list):
        return [_normalize(x) for x in obj]
    return obj


async def _list_tools_payload():
    """
    Use the public FastMCP API to fetch tools schemas.
    Works across FastMCP versions by handling sync/async returns and different shapes.
    """
    res = mcp.list_tools()
    if inspect.isawaitable(res):
        res = await res

    # Possible shapes:
    # 1) {"tools": [...]}  (MCP-style)
    # 2) [...]            (already a list)
    if isinstance(res, dict) and "tools" in res:
        tools = res["tools"]
    elif isinstance(res, list):
        tools = res
    else:
        raise AssertionError(f"Unexpected list_tools() result shape: {type(res)}")

    payload = []
    for t in tools:
        # tools are often dict-like with keys: name, description, inputSchema, outputSchema
        if isinstance(t, dict):
            payload.append(
                {
                    "name": t.get("name"),
                    "description": t.get("description"),
                    "inputSchema": t.get("inputSchema"),
                    "outputSchema": t.get("outputSchema"),
                }
            )
        else:
            # fallback if tool is an object
            payload.append(
                {
                    "name": getattr(t, "name", None),
                    "description": getattr(t, "description", None),
                    "inputSchema": getattr(t, "inputSchema", None),
                    "outputSchema": getattr(t, "outputSchema", None),
                }
            )

    payload = [p for p in payload if p.get("name")]
    payload.sort(key=lambda x: x["name"])
    return _normalize(payload)


def test_tools_schema_snapshot():
    normalized = anyio.run(_list_tools_payload)

    if not SNAP.exists():
        SNAP.parent.mkdir(parents=True, exist_ok=True)
        SNAP.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
        )
        raise AssertionError(f"Snapshot created at {SNAP}. Re-run tests.")

       

    expected = json.loads(SNAP.read_text(encoding="utf-8"))
    assert normalized == expected
