from grounded_context_mcp.tools.git_insights import git_insights, _parse_status_files


def test_parse_status_files_deduplicates_and_keeps_order():
    lines = [
        " M src/a.py",
        "?? src/b.py",
        " M src/a.py",
    ]

    out = _parse_status_files(lines)
    assert out == ["src/a.py", "src/b.py"]


def test_git_insights_structure(monkeypatch, tmp_path):
    def fake_run_git(root, args, timeout_s=2.0):
        if "status" in args:
            return " M src/x.py"
        if "show" in args:
            return "src/y.py"
        if "rev-parse" in args:
            return "main"
        if "log" in args:
            return "abc Initial commit"
        return ""

    monkeypatch.setattr(
        "grounded_context_mcp.tools.git_insights.run_git",
        fake_run_git,
    )

    out = git_insights(str(tmp_path))

    assert out["ok"] is True
    assert out["branch"] == "main"
    assert out["dirty"] is True
    assert out["worktree_changed_files"] == ["src/x.py"]
    assert out["last_commit_files"] == ["src/y.py"]
