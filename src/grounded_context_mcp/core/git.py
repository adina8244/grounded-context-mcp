# import logging, os, subprocess, sys, time
# from pathlib import Path
# from typing import List

# logger = logging.getLogger("grounded_context_mcp.git")

# def _ensure_logging_configured() -> None:
#     if logger.handlers:
#         return
#     h = logging.StreamHandler(sys.stderr)
#     h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
#     logger.addHandler(h)
#     logger.setLevel(logging.INFO)

# def _kill_process_tree_windows(pid: int) -> None:
#     # הורג את כל עץ התהליך (git + ילדים) – זה מה שעושה את זה יציב ב-Windows
#     subprocess.run(
#         ["taskkill", "/PID", str(pid), "/T", "/F"],
#         capture_output=True,
#         text=True,
#     )

# def run_git(root: Path, args: List[str], timeout_s: float = 2.0) -> str:
#     _ensure_logging_configured()

#     cmd = ["git", *args]
#     env = os.environ.copy()
#     env["GIT_TERMINAL_PROMPT"] = "0"

#     start = time.perf_counter()
#     logger.info("git: start cwd=%s cmd=%s timeout=%.1fs", root, cmd, timeout_s)

#     p = subprocess.Popen(
#         cmd,
#         cwd=str(root),
#         stdin=subprocess.DEVNULL,          # חשוב! שלא יחכה לקלט
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE,
#         text=True,
#         env=env,
#     )

#     try:
#         out, err = p.communicate(timeout=timeout_s)
#         elapsed_ms = (time.perf_counter() - start) * 1000.0

#         if p.returncode != 0:
#             logger.warning("git: nonzero rc=%s elapsed=%.1fms", p.returncode, elapsed_ms)
#             return f"[git error] rc={p.returncode} stdout={out.strip()!r} stderr={err.strip()!r}"

#         logger.info("git: ok elapsed=%.1fms out_len=%d", elapsed_ms, len(out))
#         return out

#     except subprocess.TimeoutExpired:
#         elapsed_ms = (time.perf_counter() - start) * 1000.0
#         logger.error("git: TIMEOUT elapsed=%.1fms pid=%s cwd=%s cmd=%s", elapsed_ms, p.pid, root, cmd)

#         # חובה ב-Windows: להרוג עץ תהליכים
#         try:
#             _kill_process_tree_windows(p.pid)
#         except Exception:
#             pass

#         return f"[git timeout] cmd={cmd} timeout_s={timeout_s}"

from __future__ import annotations
import os
import subprocess
import time
from pathlib import Path
from typing import List


def _kill_process_tree_windows(pid: int) -> None:
    """
    Kill a process tree on Windows (git may spawn helper processes).
    """
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
    )


def run_git(root: Path, args: List[str], timeout_s: float = 2.0) -> str:
    """
    Run a git command safely and return stdout.
    """
    cmd = ["git", *args]
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    start = time.perf_counter()
    p = subprocess.Popen(
        cmd,
        cwd=str(root),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        out, err = p.communicate(timeout=timeout_s)

        if p.returncode != 0:
            return (
                f"[git error] rc={p.returncode} "
                f"stdout={(out or '').strip()!r} "
                f"stderr={(err or '').strip()!r}"
            )

        return out or ""

    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                _kill_process_tree_windows(p.pid)
            else:
                p.kill()
        except Exception:
            pass

        return f"[git timeout] cmd={cmd} timeout_s={timeout_s}"

    except Exception as e:
        return f"[git error] {type(e).__name__}: {e}"
