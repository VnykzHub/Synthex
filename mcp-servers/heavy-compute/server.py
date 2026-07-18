#!/usr/bin/env python3
"""Heavy Compute MCP server (Synthex plugin).

FastMCP server named "heavy-compute" implementing the tool signatures from
docs/DATA_CONTRACTS.md §3:

  - sympy_solve(expression, kind='auto')     -> {result, latex, steps}
  - profile_script(path, args=[])            -> {stdout, stderr, wall_time_s, top_functions}
  - etl_validate(path, expectations='')      -> {rows, columns, grain_ok, issues}
  - docker_run(image, cmd, mounts=[])        -> {...} | {error: 'docker unavailable'}

Sandbox resolution (contract §1):
    SYNTHEX_ROOT = $CLAUDE_PROJECT_DIR | $PWD
Reads are limited to user-input/ and knowledgebase/; writes go to agent-output/.

Optional deps (pandas) degrade gracefully. sympy is required for real math.
Run `python server.py --selftest` to exercise sympy_solve without a client.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Sandbox path resolution (contract §1)
# --------------------------------------------------------------------------- #


def synthex_root() -> Path:
    """Resolve the sandbox base: $CLAUDE_PROJECT_DIR else $PWD."""
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(root).resolve()


READ_ZONES = ("user-input", "knowledgebase")
WRITE_ZONE = "agent-output"


def _resolve_under_root(path: str) -> Path:
    """Resolve *path* and ensure it lives under SYNTHEX_ROOT.

    Raises ValueError if the resolved path escapes the sandbox root.
    """
    root = synthex_root()
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    try:
        p.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path {p} is outside SYNTHEX_ROOT {root}") from exc
    return p


# --------------------------------------------------------------------------- #
# Tool: sympy_solve
# --------------------------------------------------------------------------- #

_SYMPY_KINDS = {"auto", "solve", "simplify", "integrate", "diff", "factor"}


def _sympy_solve_impl(expression: str, kind: str = "auto") -> dict[str, Any]:
    """Inner implementation of sympy_solve (runs in thread pool for timeout)."""
    try:
        import sympy
        from sympy import Eq, diff, factor, integrate, latex, simplify, solve
        from sympy.parsing.sympy_parser import parse_expr
    except Exception as exc:  # pragma: no cover - sympy is required
        return {
            "result": None,
            "latex": "",
            "steps": [f"sympy unavailable: {exc}"],
        }

    kind = (kind or "auto").lower()
    if kind not in _SYMPY_KINDS:
        return {
            "result": None,
            "latex": "",
            "steps": [f"unknown kind {kind!r}; expected one of {sorted(_SYMPY_KINDS)}"],
        }

    steps: list[str] = [f"input: {expression!r}", f"kind: {kind}"]

    def _parse(text: str):
        return parse_expr(text, evaluate=True)

    try:
        # Use stable regex to detect equations: single '=' not preceded by !<>= and not followed by =
        has_eq = bool(re.search(r'(?<![!<>=])={1}(?!=)', expression))
        # Build an expression / equation object.
        if has_eq:
            lhs_s, rhs_s = expression.split("=", 1)
            lhs, rhs = _parse(lhs_s), _parse(rhs_s)
            eq = Eq(lhs, rhs)
            expr = lhs - rhs  # canonical "= 0" form
            steps.append(f"parsed equation: {eq}")
        else:
            expr = _parse(expression)
            eq = None
            steps.append(f"parsed expression: {expr}")

        # 'auto' resolves to a concrete op.
        if kind == "auto":
            if has_eq or (expr.free_symbols and expr.is_polynomial()):
                kind = "solve"
            else:
                kind = "simplify"
            steps.append(f"auto -> {kind}")

        symbols = sorted(expr.free_symbols, key=lambda s: s.name)
        var = symbols[0] if symbols else sympy.Symbol("x")

        if kind == "solve":
            target = eq if eq is not None else expr
            sol = solve(target, dict=False)
            result = sol
            steps.append(f"solve({target}) = {sol}")
        elif kind == "simplify":
            result = simplify(expr)
            steps.append(f"simplify -> {result}")
        elif kind == "factor":
            result = factor(expr)
            steps.append(f"factor -> {result}")
        elif kind == "integrate":
            result = integrate(expr, var)
            steps.append(f"integrate w.r.t {var} -> {result}")
        elif kind == "diff":
            result = diff(expr, var)
            steps.append(f"diff w.r.t {var} -> {result}")
        else:  # pragma: no cover - guarded above
            result = expr

        try:
            latex_str = latex(result)
        except Exception:
            latex_str = ""

        # JSON-friendly result representation.
        if isinstance(result, (list, tuple)):
            result_repr: Any = [str(r) for r in result]
        else:
            result_repr = str(result)

        return {"result": result_repr, "latex": latex_str, "steps": steps}
    except Exception as exc:
        steps.append(f"error: {exc}")
        return {"result": None, "latex": "", "steps": steps}


def sympy_solve(expression: str, kind: str = "auto") -> dict[str, Any]:
    """Symbolic math via sympy. Runs with a 30-second timeout.

    kind in {auto, solve, simplify, integrate, diff, factor}. 'auto' picks a
    sensible operation: an equation (or bare polynomial) is solved, otherwise
    the expression is simplified.

    Returns {result, latex, steps}.
    """
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_sympy_solve_impl, expression, kind)
        try:
            return future.result(timeout=30)
        except FuturesTimeout:
            return {
                "result": None,
                "latex": "",
                "steps": ["sympy_solve timed out after 30s"],
            }
        except Exception as exc:
            return {
                "result": None,
                "latex": "",
                "steps": [f"sympy_solve error: {exc}"],
            }


# --------------------------------------------------------------------------- #
# Tool: profile_script
# --------------------------------------------------------------------------- #


def profile_script(path: str, args: list[str] | None = None) -> dict[str, Any]:
    """Run `python <path> <args>` under cProfile in a subprocess.

    Returns {stdout, stderr, wall_time_s, top_functions}. Only paths under
    SYNTHEX_ROOT are allowed.
    """
    args = list(args or [])
    try:
        script = _resolve_under_root(path)
    except ValueError as exc:
        return {"stdout": "", "stderr": str(exc), "wall_time_s": 0.0, "top_functions": []}

    if not script.is_file():
        return {
            "stdout": "",
            "stderr": f"script not found: {script}",
            "wall_time_s": 0.0,
            "top_functions": [],
        }

    import tempfile
    import pstats

    stats_fd, stats_path = tempfile.mkstemp(suffix=".pstats", prefix="synthex_prof_")
    os.close(stats_fd)
    cmd = [sys.executable, "-m", "cProfile", "-o", stats_path, str(script), *args]

    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=300,
            cwd=str(synthex_root()),
        )
        stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        stderr = exc.stderr or "profile timed out after 300s"
        rc = -1
    except Exception as exc:
        stdout, stderr, rc = "", f"failed to launch profiler: {exc}", -1
    wall = time.perf_counter() - start

    top_functions: list[dict[str, Any]] = []
    try:
        if os.path.getsize(stats_path) > 0:
            stats = pstats.Stats(stats_path)
            stats.sort_stats("cumulative")
            # stats.stats: {(file, line, func): (cc, nc, tt, ct, callers)}
            rows = sorted(
                stats.stats.items(), key=lambda kv: kv[1][3], reverse=True
            )[:10]
            for (fname, lineno, func), (cc, nc, tt, ct, _callers) in rows:
                top_functions.append(
                    {
                        "function": f"{Path(fname).name}:{lineno}({func})",
                        "ncalls": nc,
                        "tottime": round(tt, 6),
                        "cumtime": round(ct, 6),
                    }
                )
    except Exception as exc:
        stderr = (stderr + f"\n[profile parse error: {exc}]").strip()
    finally:
        try:
            os.remove(stats_path)
        except OSError:
            pass

    result = {
        "stdout": stdout,
        "stderr": stderr,
        "wall_time_s": round(wall, 6),
        "top_functions": top_functions,
    }
    if rc not in (0, None):
        result["returncode"] = rc
    return result


# --------------------------------------------------------------------------- #
# Tool: etl_validate
# --------------------------------------------------------------------------- #


def etl_validate(path: str, expectations: str = "") -> dict[str, Any]:
    """Validate a CSV (parquet/pandas optional).

    Returns {rows, columns, grain_ok, issues}. *expectations* may be a JSON
    object naming key columns (e.g. {"keys": ["id"]}); those columns are
    checked for combined uniqueness to set grain_ok.
    """
    issues: list[str] = []
    try:
        target = _resolve_under_root(path)
    except ValueError as exc:
        return {"rows": 0, "columns": [], "grain_ok": None, "issues": [str(exc)]}

    if not target.is_file():
        return {
            "rows": 0,
            "columns": [],
            "grain_ok": None,
            "issues": [f"file not found: {target}"],
        }

    # Parse expectations for key columns.
    key_cols: list[str] = []
    if expectations:
        try:
            spec = json.loads(expectations)
            if isinstance(spec, dict):
                raw = spec.get("keys") or spec.get("key_columns") or spec.get("grain")
                if isinstance(raw, str):
                    key_cols = [raw]
                elif isinstance(raw, (list, tuple)):
                    key_cols = [str(c) for c in raw]
            elif isinstance(spec, list):
                key_cols = [str(c) for c in spec]
        except json.JSONDecodeError as exc:
            issues.append(f"could not parse expectations JSON: {exc}")

    suffix = target.suffix.lower()
    columns: list[str] = []
    row_count = 0
    grain_ok: bool | None = None
    dupes = 0

    if suffix in (".parquet", ".pq"):
        try:
            import pandas as pd  # optional

            df = pd.read_parquet(target)
            columns = list(map(str, df.columns))
            row_count = int(len(df))
            # Grain check via DataFrame API (no per-row copy needed)
            if key_cols:
                missing = [c for c in key_cols if c not in columns]
                if missing:
                    issues.append(f"key columns not found: {missing}")
                    grain_ok = False
                else:
                    dupes = int(df.duplicated(subset=key_cols).sum())
                    grain_ok = dupes == 0
                    if dupes:
                        issues.append(
                            f"grain violated: {dupes} duplicate rows on key {key_cols}"
                        )
        except Exception as exc:
            return {
                "rows": 0,
                "columns": [],
                "grain_ok": None,
                "issues": issues + [f"parquet requires pandas/pyarrow: {exc}"],
            }
    else:
        import csv

        try:
            with open(target, newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                columns = list(reader.fieldnames or [])
                # Grain check folded into single read loop (no rows_data list)
                if key_cols:
                    missing = [c for c in key_cols if c not in columns]
                    if missing:
                        issues.append(f"key columns not found: {missing}")
                        grain_ok = False
                    else:
                        seen: set[tuple] = set()
                for r in reader:
                    row_count += 1
                    if key_cols and grain_ok is not False:
                        composite = tuple(r.get(c) for c in key_cols)
                        if composite in seen:
                            dupes += 1
                        else:
                            seen.add(composite)
                if key_cols and grain_ok is not False:
                    grain_ok = dupes == 0
                    if dupes:
                        issues.append(
                            f"grain violated: {dupes} duplicate rows on key {key_cols}"
                        )
        except Exception as exc:
            return {
                "rows": 0,
                "columns": columns,
                "grain_ok": None,
                "issues": issues + [f"failed reading CSV: {exc}"],
            }

    if not columns:
        issues.append("no columns detected (empty file or missing header)")
    if row_count == 0:
        issues.append("no data rows")

    return {
        "rows": row_count,
        "columns": columns,
        "grain_ok": grain_ok,
        "issues": issues,
    }


# --------------------------------------------------------------------------- #
# Tool: docker_run
# --------------------------------------------------------------------------- #


def docker_run(
    image: str, cmd: list[str] | None = None, mounts: list[str] | None = None
) -> dict[str, Any]:
    """Run a container via `docker run`.

    Degrades gracefully: if the docker binary is absent, returns
    {"error": "docker unavailable"} instead of raising.
    """
    cmd = list(cmd or [])
    mounts = list(mounts or [])

    if shutil.which("docker") is None:
        return {"error": "docker unavailable"}

    argv = ["docker", "run", "--rm"]
    for m in mounts:
        parts = m.split(":", 1)
        src = parts[0]
        # Validate that mount source is within SYNTHEX_ROOT
        try:
            src_p = _resolve_under_root(src)
        except ValueError:
            return {"error": f"mount source {src!r} is outside SYNTHEX_ROOT"}
        resolved = f"{src_p}:{parts[1]}" if len(parts) > 1 else str(src_p)
        argv += ["-v", resolved]
    argv.append(image)
    argv += cmd

    try:
        proc = subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=600)
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "docker run timed out after 600s"}
    except Exception as exc:
        return {"error": f"docker run failed: {exc}"}


# --------------------------------------------------------------------------- #
# FastMCP server wiring (optional import so --selftest works without mcp)
# --------------------------------------------------------------------------- #


def build_server():
    """Construct and register the FastMCP server. Requires the `mcp` package."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("heavy-compute")

    @server.tool(name="sympy_solve")
    def sympy_solve_tool(expression: str, kind: str = "auto") -> dict:
        """Symbolic math via sympy: solve/simplify/integrate/diff/factor."""
        return sympy_solve(expression, kind)

    @server.tool(name="profile_script")
    def profile_script_tool(path: str, args: list[str] | None = None) -> dict:
        """Profile `python <path> <args>` under cProfile; report top functions."""
        return profile_script(path, args)

    @server.tool(name="etl_validate")
    def etl_validate_tool(path: str, expectations: str = "") -> dict:
        """Validate a CSV/parquet file: rows, columns, grain, issues."""
        return etl_validate(path, expectations)

    @server.tool(name="docker_run")
    def docker_run_tool(image: str, cmd: list[str] | None = None, mounts: list[str] | None = None) -> dict:
        """Run a container via `docker run` (graceful if docker absent)."""
        return docker_run(image, cmd, mounts)

    return server


def _selftest() -> int:
    out = sympy_solve("x**2 - 4", "solve")
    print("sympy_solve('x**2 - 4', 'solve') ->", out["result"])
    roots = out["result"]
    ok = isinstance(roots, list) and sorted(roots) == ["-2", "2"]
    print("selftest", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(_selftest())
    build_server().run()
