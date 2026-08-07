"""End-to-end replication pipeline: paper -> verdict.

Wires extract + codegen + sandbox + backtest into a single function callable
from CLI. Uses fallback paths so it runs without ANTHROPIC_API_KEY for testing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from .backtest import run_signal_backtest, BacktestResult
from .extract.pdf import download_pdf, extract_text
from .extract.spec import extract_spec, extract_spec_offline, SignalSpec
from .extract.codegen import generate_signal_code, validate_code, fallback_code
from .claims import Claim
from .extract.sandbox import run_inline


@dataclass
class ReplicationReport:
    paper_id: str
    paper_title: Optional[str] = None
    pdf_path: Optional[str] = None
    spec: Optional[dict] = None
    spec_agreement: Optional[float] = None
    code: Optional[str] = None
    code_validation: Optional[dict] = None
    code_attempts: list[str] = field(default_factory=list)
    sandbox_error: Optional[str] = None
    backtest: Optional[dict] = None
    verdict: Optional[str] = None
    verdict_reasoning: list[str] = field(default_factory=list)
    # What the paper claimed, next to what we got, next to what survives the
    # corrections the paper did not run. See claims.py.
    claim_check: Optional[dict] = None
    pipeline_status: str = "pending"   # pending | spec_failed | codegen_failed | sandbox_failed | backtest_failed | done
    pipeline_errors: list[str] = field(default_factory=list)


def _run_backtest(spec: SignalSpec, code: str, fixture_metadata: dict | None = None) -> tuple[Optional[BacktestResult], Optional[str]]:
    """Execute generated code via sandbox and run backtest."""
    from .data import load_universe, load_price_panel
    universe_name = spec.universe or "sp500"
    tickers = load_universe(universe_name)
    if not tickers:
        return None, f"no tickers for universe {universe_name}"

    # Pre-load prices to validate `signal()` runs cleanly with the type the
    # backtest engine will use; the actual backtest re-loads via runner.
    prices = load_price_panel(tickers=tickers, start="2014-01-01", end="2026-04-01").ffill(limit=5).dropna(how="all", axis=1)
    if prices.shape[1] == 0:
        return None, "empty price panel"

    # Compile + dry-run signal()
    sig_df, err = run_inline(code, prices)
    if err:
        return None, f"sandbox: {err}"
    if sig_df.shape != prices.shape:
        return None, f"signal shape mismatch: {sig_df.shape} vs {prices.shape}"

    # Bind to a closure for the backtest engine
    def signal_fn(prices_inner):
        out, e = run_inline(code, prices_inner)
        if e:
            raise RuntimeError(e)
        return out

    horizon = spec.horizon_days or 21
    long_only = not (spec.is_long_short if spec.is_long_short is not None else True)
    expected_sharpe = None
    if fixture_metadata and "expected_sharpe" in fixture_metadata:
        expected_sharpe = fixture_metadata["expected_sharpe"]

    result = run_signal_backtest(
        signal_fn=signal_fn,
        signal_name=spec.formula or "auto-replicated",
        universe=universe_name,
        start="2014-01-01",
        end="2026-04-01",
        horizon_days=horizon,
        cost_bps=5.0,
        n_trials_for_dsr=1,
        long_only=long_only,
        expected_sharpe=expected_sharpe,
        oos_split_date="2024-01-01",
    )
    return result, None


def _check_claim(result: BacktestResult, claim: "Claim | None") -> Optional[dict]:
    """Score the replication against the paper, if we know what it claimed.

    Reproducing a number is the easy half. This is the other half: whether the
    published result survives a Newey-West t, every held-out stretch of the
    sample, and the trial count behind it.
    """
    if claim is None or not result.daily_returns:
        return None
    try:
        from .claims import verify
        return verify(claim, result.daily_returns, trials=1).as_dict()
    except Exception as exc:  # noqa: BLE001 - a failed check must not sink the run
        return {"status": "ERROR", "reasons": [f"{type(exc).__name__}: {exc}"]}


def replicate(
    paper_id: str,
    pdf_url: str,
    title: Optional[str] = None,
    *,
    use_llm: bool = True,
    fixture_metadata: dict | None = None,
    claim: "Claim | None" = None,
) -> ReplicationReport:
    """End-to-end: download PDF, extract spec, generate code, run backtest.
    Set use_llm=False to run with offline-extract + fallback-code (testing path).
    """
    rpt = ReplicationReport(paper_id=paper_id, paper_title=title)

    # 1. PDF
    try:
        pdf = download_pdf(pdf_url, paper_id)
        rpt.pdf_path = str(pdf)
        text = extract_text(pdf, max_pages=30)
        if len(text) < 500:
            rpt.pipeline_status = "spec_failed"
            rpt.pipeline_errors.append(f"pdf text too short ({len(text)} chars)")
            return rpt
    except Exception as e:
        rpt.pipeline_status = "spec_failed"
        rpt.pipeline_errors.append(f"pdf download/extract: {e}")
        return rpt

    # 2. Spec extraction
    try:
        if use_llm:
            spec, agreement, debug = extract_spec(text)
            rpt.spec_agreement = agreement
            rpt.spec = asdict(spec)
            if agreement < 0.85:
                rpt.pipeline_errors.append(f"low spec agreement: {agreement:.2f}, flag for review")
        else:
            spec = extract_spec_offline(text)
            rpt.spec_agreement = 1.0
            rpt.spec = asdict(spec)
    except Exception as e:
        rpt.pipeline_status = "spec_failed"
        rpt.pipeline_errors.append(f"extract: {e}")
        return rpt

    if not spec.is_complete():
        rpt.pipeline_errors.append("spec incomplete (missing required fields)")
        if not use_llm:
            # Use fallback for testing
            rpt.pipeline_errors.append("offline mode: filling defaults to use fallback code")
            spec.universe = spec.universe or "sp500"
            spec.horizon_days = spec.horizon_days or 21
            spec.expected_sign = spec.expected_sign or "+"
            spec.is_long_short = True if spec.is_long_short is None else spec.is_long_short
            spec.is_cross_sectional = True if spec.is_cross_sectional is None else spec.is_cross_sectional

    # 3. Code generation
    try:
        if use_llm:
            code, val, attempts = generate_signal_code(spec)
            rpt.code = code
            rpt.code_validation = {"ok": val.ok, "errors": val.errors, "warnings": val.warnings}
            rpt.code_attempts = attempts
            if not val.ok:
                rpt.pipeline_status = "codegen_failed"
                rpt.pipeline_errors.append(f"codegen invalid after retries: {val.errors[:2]}")
                return rpt
        else:
            code = fallback_code()
            val = validate_code(code)
            rpt.code = code
            rpt.code_validation = {"ok": val.ok, "errors": val.errors, "warnings": val.warnings}
    except Exception as e:
        rpt.pipeline_status = "codegen_failed"
        rpt.pipeline_errors.append(f"codegen: {e}")
        return rpt

    # 4. Backtest
    try:
        result, err = _run_backtest(spec, code, fixture_metadata=fixture_metadata)
        if err:
            rpt.pipeline_status = "backtest_failed"
            rpt.pipeline_errors.append(err)
            return rpt
        rpt.backtest = {
            "sharpe": result.sharpe,
            "sharpe_oos": result.sharpe_oos,
            "ann_return": result.ann_return,
            "ann_vol": result.ann_vol,
            "max_drawdown": result.max_drawdown,
            "ic_mean": result.ic_report.ic_mean,
            "icir": result.ic_report.icir,
            "dsr": result.dsr.get("dsr"),
            "replication_score": result.replication_score,
        }
        rpt.verdict = result.verdict
        rpt.verdict_reasoning = result.verdict_reasoning
        rpt.claim_check = _check_claim(result, claim)
        rpt.pipeline_status = "done"
    except Exception as e:
        rpt.pipeline_status = "backtest_failed"
        rpt.pipeline_errors.append(f"backtest: {type(e).__name__}: {e}")
    return rpt


if __name__ == "__main__":
    # Demo: run end-to-end on a known arXiv paper, offline mode (no API needed)
    rpt = replicate(
        paper_id="momentum_jt1993_demo",
        pdf_url="https://arxiv.org/pdf/2403.16527.pdf",  # placeholder, any q-fin paper works
        title="(demo paper)",
        use_llm=False,
        fixture_metadata={"expected_sharpe": (0.4, 0.9)},
    )
    import json
    print(json.dumps(asdict(rpt), indent=2, default=str))
