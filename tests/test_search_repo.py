from grounded_context_mcp.tools.search_repo import search_repo


def test_search_repo_finds_match(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("def hello(): pass")

    out = search_repo("hello", root=str(tmp_path))

    assert out["query"] == "hello"
    assert len(out["results"]) == 1
    assert out["results"][0]["path"] == "a.py"
