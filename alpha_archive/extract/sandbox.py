"""Sandbox executor for LLM-generated `signal` code.

MVP: in-process exec with restricted globals + timeout. Production: Docker.
Returns the `signal` callable on success, error string on failure.
"""
from __future__ import annotations

import builtins
import multiprocessing
from typing import Callable, Optional

import numpy as np
import pandas as pd


# Whitelist of safe builtins
SAFE_BUILTINS = {
    name: getattr(builtins, name) for name in [
        "abs", "all", "any", "bool", "bytes", "callable", "chr",
        "complex", "dict", "divmod", "enumerate", "filter", "float",
        "format", "frozenset", "hash", "hex", "id", "int", "isinstance",
        "issubclass", "iter", "len", "list", "map", "max", "min", "next",
        "object", "oct", "ord", "pow", "print", "range", "repr",
        "reversed", "round", "set", "slice", "sorted", "str", "sum",
        "tuple", "type", "zip",
        "True", "False", "None",
        "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
        "ZeroDivisionError", "ArithmeticError",
    ]
}
SAFE_BUILTINS["__import__"] = builtins.__import__  # required for `import pandas as pd`


def load_signal_callable(code: str) -> tuple[Optional[Callable], Optional[str]]:
    """Compile + load the `signal` callable from generated code.
    Returns (callable, None) on success or (None, error_message) on failure.
    """
    safe_globals = {
        "__builtins__": SAFE_BUILTINS,
        "__name__": "alpha_archive_sandbox",
    }
    try:
        compiled = compile(code, "<sandbox>", "exec")
    except SyntaxError as e:
        return None, f"syntax error: {e}"
    try:
        exec(compiled, safe_globals)
    except Exception as e:
        return None, f"import/setup error: {type(e).__name__}: {e}"
    fn = safe_globals.get("signal")
    if fn is None or not callable(fn):
        return None, "no callable named `signal` defined"
    return fn, None


def _worker(code: str, prices_pkl: bytes, q):
    """Subprocess target: load + run signal(prices), put result on queue."""
    import pickle
    try:
        prices = pickle.loads(prices_pkl)
        fn, err = load_signal_callable(code)
        if err:
            q.put(("error", err))
            return
        out = fn(prices)
        q.put(("ok", pickle.dumps(out)))
    except Exception as e:
        q.put(("error", f"{type(e).__name__}: {e}"))


def run_in_sandbox(
    code: str,
    prices: pd.DataFrame,
    *,
    timeout_seconds: int = 60,
) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """Run generated `signal(prices)` in a subprocess with a hard timeout.
    Returns (signal_df, None) on success or (None, error_message) on failure.

    Note: subprocess sandboxing is best-effort on Windows; production should
    use Docker. This catches: infinite loops, segfaults, stack-overflow.
    """
    import pickle

    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue()
    prices_pkl = pickle.dumps(prices)
    p = ctx.Process(target=_worker, args=(code, prices_pkl, q))
    p.start()
    p.join(timeout_seconds)
    if p.is_alive():
        p.terminate()
        p.join(2)
        if p.is_alive():
            p.kill()
        return None, f"timeout after {timeout_seconds}s"
    try:
        status, payload = q.get_nowait()
    except Exception:
        return None, "no output from subprocess (likely crashed)"
    if status == "error":
        return None, payload
    try:
        result = pickle.loads(payload)
    except Exception as e:
        return None, f"deserialize error: {e}"
    if not isinstance(result, pd.DataFrame):
        return None, f"signal() returned {type(result).__name__}, expected DataFrame"
    return result, None


def run_inline(code: str, prices: pd.DataFrame) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """Faster path: run in-process without subprocess. Use when code already
    passed static validation. NOT a real sandbox, only catches Python errors.
    """
    fn, err = load_signal_callable(code)
    if err:
        return None, err
    try:
        out = fn(prices)
    except Exception as e:
        return None, f"runtime error: {type(e).__name__}: {e}"
    if not isinstance(out, pd.DataFrame):
        return None, f"signal() returned {type(out).__name__}, expected DataFrame"
    return out, None
