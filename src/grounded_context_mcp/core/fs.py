from __future__ import annotations

from pathlib import Path
from typing import Iterator, Optional, List, Tuple

DEFAULT_IGNORES = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", "dist", "build"
}

TEXT_EXTS = {
    ".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".js", ".ts", ".tsx",
    ".html", ".css", ".cpp", ".c", ".h", ".hpp", ".go", ".rs"
}


def iter_text_files(root: Path, file_globs: Optional[List[str]] = None) -> Iterator[Tuple[Path, str]]:
    root = root.resolve()
    for p in root.rglob("*"):
        if any(part in DEFAULT_IGNORES for part in p.parts):
            continue
        if not p.is_file():
            continue

        if file_globs:
            if not any(p.match(g) for g in file_globs):
                continue
        else:
            if p.suffix.lower() not in TEXT_EXTS:
                continue

        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        yield p, text


def read_file_safe(path: Path) -> Optional[str]:
    try:
        if not path.exists() or not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
