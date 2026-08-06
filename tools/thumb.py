"""Generate the per-paper thumbnail that sits in the left column of a card.

Papers With Code renders the paper's first page there. We cannot reproduce a
copyrighted page, and a picture of a PDF says nothing anyway, so the slot shows
the result instead: what the paper claimed against what we measured.

Inline SVG, no images to host and no requests to make.
"""

from __future__ import annotations

import html

W, H = 240, 168
PAD = 14


def _shell(body: str, caption: str) -> str:
    return (
        f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
        f'aria-label="{html.escape(caption)}" preserveAspectRatio="xMidYMid meet">'
        f'<rect width="{W}" height="{H}" fill="none"/>{body}</svg>'
    )


def _label(x: int, y: int, text: str, size: float = 8.0, fill: str = "#8a97a3",
           anchor: str = "start", weight: int = 400) -> str:
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}" font-family="ui-monospace,Menlo,Consolas,monospace">'
            f"{html.escape(text)}</text>")


def two_bars(claimed: float, measured: float, unit: str = "%/mo") -> str:
    """Claimed against measured, on a shared zero-centred scale."""
    top, row = 46, 34
    axis_x = PAD + 44
    value_col = 56                      # space kept clear for the printed number
    span = W - axis_x - PAD - value_col
    scale = max(abs(claimed), abs(measured), 0.01)
    half = span / 2
    zero = axis_x + half

    parts = [
        _label(PAD, 22, "CLAIM VS MEASURED", 8.5, "#61707e", weight=700),
        f'<line x1="{zero}" y1="{top - 10}" x2="{zero}" y2="{top + row + 16}" '
        f'stroke="#e3e7eb" stroke-width="1"/>',
    ]
    for i, (name, value, colour) in enumerate(
        [("paper", claimed, "#0f7a45"), ("ours", measured, "#a5231a")]
    ):
        y = top + i * row
        length = abs(value) / scale * (half - 6)
        x = zero if value >= 0 else zero - length
        parts += [
            _label(PAD, y + 9, name, 9, "#61707e"),
            f'<rect x="{x:.1f}" y="{y}" width="{max(length, 1.2):.1f}" height="12" '
            f'rx="2" fill="{colour}" opacity="0.85"/>',
            _label(W - PAD, y + 9, f"{value:+.2f}{unit}", 8.5,
                   colour, anchor="end", weight=700),
        ]
    parts.append(_label(PAD, H - PAD, "zero marked; bars share a scale", 7.5, "#aab4bd"))
    return _shell("".join(parts), f"paper {claimed}, measured {measured}")


def _clip(text: str, limit: int) -> str:
    """Trim to a word boundary; a name cut mid-token reads as a rendering bug."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]).rstrip(" (,-") + "…"


def intervals(rows: list[tuple[str, tuple[float, float], tuple[float, float]]]) -> str:
    """Paper interval above ours, per family, on one shared axis."""
    everything = [v for _, a, b in rows for v in (*a, *b)]
    lo, hi = min(everything + [0.0]), max(everything + [0.0])
    pad = (hi - lo) * 0.12 or 0.1
    lo, hi = lo - pad, hi + pad

    axis_x, axis_w = PAD + 4, W - 2 * PAD - 8
    def px(v: float) -> float:
        return axis_x + (v - lo) / (hi - lo) * axis_w

    parts = [_label(PAD, 20, "95% INTERVALS", 8.5, "#61707e", weight=700)]
    if lo < 0 < hi:
        parts.append(f'<line x1="{px(0):.1f}" y1="28" x2="{px(0):.1f}" y2="{H - 26}" '
                     f'stroke="#e3e7eb" stroke-width="1"/>')

    y = 36
    for name, paper, ours in rows:
        parts.append(_label(PAD, y, _clip(name, 24), 8, "currentColor", weight=700))
        y += 9
        for (a, b), colour in ((paper, "#61707e"), (ours, "#0b5fd0")):
            x1, x2 = px(a), px(b)
            parts += [
                f'<line x1="{x1:.1f}" y1="{y}" x2="{x2:.1f}" y2="{y}" '
                f'stroke="{colour}" stroke-width="3" stroke-linecap="round"/>',
                f'<line x1="{x1:.1f}" y1="{y - 3}" x2="{x1:.1f}" y2="{y + 3}" '
                f'stroke="{colour}" stroke-width="1"/>',
                f'<line x1="{x2:.1f}" y1="{y - 3}" x2="{x2:.1f}" y2="{y + 3}" '
                f'stroke="{colour}" stroke-width="1"/>',
            ]
            y += 11
        y += 6

    parts += [
        f'<line x1="{axis_x}" y1="{H - 20}" x2="{axis_x + axis_w}" y2="{H - 20}" '
        f'stroke="#e3e7eb"/>',
        _label(axis_x, H - 10, f"{lo:+.2f}", 7.5, "#aab4bd"),
        _label(axis_x + axis_w, H - 10, f"{hi:+.2f}", 7.5, "#aab4bd", anchor="end"),
        _label(W // 2, 30, "grey = paper   blue = ours", 7.5, "#aab4bd", anchor="middle"),
    ]
    return _shell("".join(parts), "confidence intervals, paper against ours")


def for_record(rec: dict) -> str:
    if "families" in rec:
        return intervals([
            (f["label"], tuple(f["paper_sharpe_ci"]), tuple(f["sharpe_ci"]))
            for f in rec["families"]
        ])
    return two_bars(rec["claimed_monthly_pct"], rec["measured_monthly_pct"])
