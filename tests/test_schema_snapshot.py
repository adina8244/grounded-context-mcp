import json
import inspect
from pathlib import Path

import anyio

from grounded_context_mcp.server import mcp

SNAP = Path(__file__).parent / "snapshots" / "tools_schema.json"

# Fields that are commonly auto-generated / unstable across versions
_NOISY_SCHEMA_KEYS = {"title", "default", "examples"}


def _normalize(obj):
    """
    Deterministic normalization for snapshot stability:
      - Sort dict keys
      - Strip whitespace in strings
      - Drop noisy/auto-generated schema keys (title/default/examples)
    """
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            if k in _NOISY_SCHEMA_KEYS:
                continue
            cleaned[k] = _normalize(v)
        return {k: cleaned[k] for k in sorted(cleaned)}

    if isinstance(obj, list):
        return [_normalize(x) for x in obj]

    if isinstance(obj, str):
        return obj.strip()

    return obj


def _norm_text(x):
    if isinstance(x, str):
        return x.strip()
    return x


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
        if isinstance(t, dict):
            payload.append(
                {
                    "name": t.get("name"),
                    "description": _norm_text(t.get("description")),
                    "inputSchema": t.get("inputSchema"),
                    "outputSchema": t.get("outputSchema"),
                }
            )
        else:
            payload.append(
                {
                    "name": getattr(t, "name", None),
                    "description": _norm_text(getattr(t, "description", None)),
                    "inputSchema": getattr(t, "inputSchema", None),
                    "outputSchema": getattr(t, "outputSchema", None),
                }
            )

    payload = [p for p in payload if p.get("name")]
    payload.sort(key=lambda x: x["name"])

    # Deep normalize (sort keys, strip strings, remove noisy schema keys)
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


