"""LLM code generation: SignalSpec -> Python `signal(prices)` function.

Per actor.md §4: validates static gates BEFORE backtest. No lookahead, no
network/io, deterministic, runtime-bounded.
"""
from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from .spec import SignalSpec


CODEGEN_MODEL = "claude-sonnet-4-6"

CODEGEN_PROMPT = """You are writing a Python function that implements a trading signal from a structured specification. The function will be backtested by a standardized engine.

# Strict requirements

- ONE module-level function ONLY: `def signal(prices: pd.DataFrame) -> pd.DataFrame:`
- Input `prices`: wide DataFrame, index = pd.Timestamp dates (sorted ascending), columns = tickers, values = adjusted close
- Output: DataFrame same shape as `prices`, values = signal score (higher = more bullish)
- Allowed imports: `pandas as pd`, `numpy as np`. Nothing else.
- Use ONLY past data at time t (no `.shift(-N)` for negative N anywhere)
- Deterministic (no random.* / np.random without explicit seed)
- Module-level constants OK (LOOKBACK = 252 etc.)
- NO function definitions other than `signal`
- NO calls to: open, eval, exec, __import__, urllib, requests, socket, subprocess, os.system, os.environ
- NO file I/O of any kind

# Specification

```json
{spec_json}
```

Output ONLY the Python module code (no prose, no markdown fences). Start with imports.
"""


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# Banned identifiers (substring match in source)
BANNED_TOKENS = [
    "open(", "eval(", "exec(", "__import__",
    "urllib", "requests.", "socket", "subprocess",
    "os.system", "os.environ", "os.popen",
    "input(",  # interactive
    "globals()", "locals()",
    ".write(", ".rmdir(", ".unlink(",
    "compile(",
]

# Required structure
REQUIRED_SIGNATURE = re.compile(
    r"^def\s+signal\s*\(\s*prices\s*:.*?\)\s*->\s*", re.M | re.S
)

# Lookahead: bare `.shift(-N)` not preceded by 'forward' or comment marker
LOOKAHEAD_PATTERN = re.compile(r"\.shift\s*\(\s*-\s*\d+", re.M)


def _ast_import_check(tree: ast.Module) -> list[str]:
    """Only allow `import pandas as pd` and `import numpy as np`."""
    errors = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ("pandas", "numpy"):
                    errors.append(f"disallowed import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            errors.append(f"disallowed `from X import Y`: from {node.module}")
    return errors


def _ast_function_check(tree: ast.Module) -> list[str]:
    """Allow only one top-level function named `signal`."""
    errors = []
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not funcs:
        errors.append("no function definition")
    elif len(funcs) > 1:
        errors.append(f"multiple top-level functions: {[f.name for f in funcs]}")
    elif funcs[0].name != "signal":
        errors.append(f"function must be named 'signal', got '{funcs[0].name}'")
    return errors


def validate_code(code: str) -> ValidationResult:
    """Run static checks on generated code."""
    errors, warnings = [], []

    # Banned tokens
    for tok in BANNED_TOKENS:
        if tok in code:
            errors.append(f"banned token used: {tok}")

    # Lookahead
    if LOOKAHEAD_PATTERN.search(code):
        errors.append("lookahead bias: `.shift(-N)` for negative N")

    # Signature
    if not REQUIRED_SIGNATURE.search(code):
        errors.append("missing required signature: def signal(prices: pd.DataFrame) -> ...")

    # AST checks
    try:
        tree = ast.parse(code)
        errors.extend(_ast_import_check(tree))
        errors.extend(_ast_function_check(tree))
    except SyntaxError as e:
        errors.append(f"syntax error: {e}")
        return ValidationResult(ok=False, errors=errors, warnings=warnings)

    # Heuristic warnings
    if "for " in code and "iterrows" in code:
        warnings.append("uses iterrows(), may be slow on large panels")
    if ".rolling(" not in code and ".pct_change(" not in code and ".diff(" not in code:
        warnings.append("no rolling/pct_change/diff, verify this is intentional")

    return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)


def generate_signal_code(
    spec: SignalSpec,
    *,
    max_retries: int = 3,
) -> tuple[str, ValidationResult, list[str]]:
    """Generate code; on validation failure, feed errors back to model.
    Returns (final_code, final_validation, attempt_log).
    Uses pluggable LLM provider (see alpha_archive.llm.factory.get_provider).
    """
    from dataclasses import asdict
    from ..llm import get_provider
    provider = get_provider()
    spec_json = json.dumps(asdict(spec), indent=2, default=str)
    attempts = []
    code = ""
    val = ValidationResult(ok=False, errors=["not yet generated"])

    prompt = CODEGEN_PROMPT.format(spec_json=spec_json)
    for i in range(max_retries):
        resp = provider.complete(prompt, model="sonnet", max_tokens=1500, temperature=0.0)
        code = resp.text.strip()
        if code.startswith("```"):
            code = code.split("```", 2)[1]
            if code.startswith("python"):
                code = code[6:]
            code = code.strip().rstrip("`").strip()
        val = validate_code(code)
        attempts.append(f"attempt {i+1} ({provider.name}): ok={val.ok}, errors={val.errors[:3]}")
        if val.ok:
            break
        # next iteration: include errors in prompt
        prompt = (
            CODEGEN_PROMPT.format(spec_json=spec_json)
            + f"\n\n# Previous attempt failed validation. Fix these errors:\n"
            + "\n".join(f"- {e}" for e in val.errors)
        )
    return code, val, attempts


# A trivial fallback for testing without API
FALLBACK_TEMPLATE = """import pandas as pd
import numpy as np

LOOKBACK = 252
SKIP = 21

def signal(prices: pd.DataFrame) -> pd.DataFrame:
    return (prices.shift(SKIP) / prices.shift(LOOKBACK)) - 1
"""


def fallback_code() -> str:
    """Returns a known-good momentum implementation for testing without API key."""
    return FALLBACK_TEMPLATE
