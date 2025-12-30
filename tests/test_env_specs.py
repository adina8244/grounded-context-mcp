from grounded_context_mcp.tools.env_specs import env_specs


def test_env_specs_schema():
    out = env_specs()

    assert isinstance(out, dict)
    assert out["server"] == "grounded-coding-context"
    assert out["scope"] == "local repo only"
    assert out["network"] == "disabled/not required"
    assert isinstance(out["notes"], list)
    assert "No GitHub API" in out["notes"]
