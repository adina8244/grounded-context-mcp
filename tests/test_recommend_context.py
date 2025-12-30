import pytest
from grounded_context_mcp.tools.recommend_context import recommend_context


@pytest.mark.asyncio
async def test_recommend_context_basic(tmp_path, monkeypatch):
    f = tmp_path / "service.py"
    f.write_text("def handler(): raise Exception('error')")

    monkeypatch.setattr(
        "grounded_context_mcp.tools.recommend_context.git_insights",
        lambda *_: {"ok": False},
    )

    out = await recommend_context(
        query="error",
        intent="debug",
        root=str(tmp_path),
    )

    assert out["intent"] == "debug"
    assert out["confidence"] >= 0.35
    assert len(out["recommended_files"]) >= 1
    assert "service.py" in out["recommended_files"][0]["path"]


@pytest.mark.asyncio
async def test_context_diff_mode_exposed(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "grounded_context_mcp.tools.recommend_context.git_insights",
        lambda *_: {
            "ok": True,
            "dirty": True,
            "worktree_changed_files": ["a.py"],
            "last_commit_files": ["b.py"],
        },
    )

    out = await recommend_context(
        query="anything",
        intent="debug",
        root=str(tmp_path),
    )

    paths = [x["path"] for x in out["recently_changed"]]
    assert "a.py" in paths
    assert "b.py" in paths
