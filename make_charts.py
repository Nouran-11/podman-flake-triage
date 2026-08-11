#!/usr/bin/env python3
"""Generate cover-letter figures from real pipeline output.

Every number is computed from extracted.json. Figure 2 is only drawn if
the v1/v2 comparison can actually be recomputed against my_labels.py.
"""
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("charts")
OUT.mkdir(exist_ok=True)

INK, ACCENT, MUTED = "#1a1a1a", "#2b4c7e", "#9aa7b8"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": "#cccccc", "axes.labelcolor": INK,
    "text.color": INK, "xtick.color": INK, "ytick.color": INK,
    "figure.dpi": 200,
})

rs = json.load(open("extracted.json"))
total_in = sum(r["total_lines"] for r in rs)
total_out = sum(r["excerpt_lines"] for r in rs)
pct = 100 * (1 - total_out / total_in)

print("=== measured from extracted.json ===")
print(f"failures:      {len(rs)}")
print(f"log lines in:  {total_in:,}")
print(f"log lines out: {total_out:,}")
print(f"reduction:     {pct:.2f}%")

# ---- figure 1: log reduction -------------------------------------------
fig, ax = plt.subplots(figsize=(6.5, 2.4))
ax.barh(["After extraction", "Raw CI logs"], [total_out, total_in],
        color=[ACCENT, MUTED], height=0.55)
ax.set_xscale("log")
ax.set_xlabel("log lines (log scale)")
ax.set_title(f"Log reduction across {len(rs)} real failures ({pct:.1f}% removed)",
             loc="left", fontsize=11, weight="bold")
for y, v in enumerate([total_out, total_in]):
    ax.text(v * 1.15, y, f"{v:,}", va="center", fontsize=9)
ax.set_xlim(right=total_in * 4)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "fig1_log_reduction.png", bbox_inches="tight")
plt.close(fig)

# ---- figure 2: v1 vs v2, only if recomputable ---------------------------
v1v2 = None
try:
    from my_labels import LABELS
    if len(LABELS) == len(rs):
        v1 = sum(1 for i, r in enumerate(rs)
                 if r.get("llm_category") == LABELS.get(i))
        v2 = sum(1 for i, r in enumerate(rs)
                 if r.get("llm_v2_category") == LABELS.get(i))
        v1v2 = (100 * v1 / len(LABELS), 100 * v2 / len(LABELS), len(LABELS))
    else:
        print(f"\nfig2 SKIPPED: my_labels.py has {len(LABELS)} labels but "
              f"extracted.json has {len(rs)} failures. The labels are keyed "
              f"by position, so they no longer line up. Re-label, or quote "
              f"the figures you recorded in NOTES.md at the time.")
except ImportError:
    print("\nfig2 SKIPPED: my_labels.py not found.")

if v1v2:
    a, b, n = v1v2
    print(f"prompt v1:     {a:.0f}%  (n={n})")
    print(f"prompt v2:     {b:.0f}%  (n={n})")
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    bars = ax.bar(["Prompt v1", "Prompt v2"], [a, b],
                  color=[MUTED, ACCENT], width=0.5)
    ax.set_ylim(0, 100)
    ax.set_ylabel("agreement with hand labels (%)")
    ax.set_title(f"Classifier accuracy, n={n} hand-labelled failures",
                 loc="left", fontsize=11, weight="bold")
    for bar, v in zip(bars, [a, b]):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 2, f"{v:.0f}%",
                ha="center", fontsize=10, weight="bold")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_prompt_accuracy.png", bbox_inches="tight")
    plt.close(fig)

# ---- figure 3: categories ----------------------------------------------
key = "sig_category" if any(r.get("sig_category") for r in rs) else "llm_v2_category"
counts = Counter(r.get(key) for r in rs if r.get(key))
labels, values = zip(*counts.most_common())
print(f"categories:    {dict(counts)}  (field: {key})")

fig, ax = plt.subplots(figsize=(5.4, 3.0))
bars = ax.barh(list(labels)[::-1], list(values)[::-1], color=ACCENT, height=0.6)
ax.set_xlabel("failures")
ax.set_title(f"Root-cause categories across {sum(values)} failures",
             loc="left", fontsize=11, weight="bold")
for bar, v in zip(bars, list(values)[::-1]):
    ax.text(v + 0.6, bar.get_y() + bar.get_height() / 2, str(v),
            va="center", fontsize=9)
ax.set_xlim(right=max(values) * 1.15)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "fig3_categories.png", bbox_inches="tight")
plt.close(fig)

print(f"\nwrote charts to {OUT}/")
