"""
Statistical analysis for the HRI weekly check-in study.

Run from the repository root:
    python analysis/analysis.py
or from inside the analysis/ folder:
    python analysis.py

Reads ../data/responses.csv (24 participants, 12 per condition) and reproduces
the statistics reported in the final paper:
  - Independent-samples t-tests for Perceived Empathy and Likability
  - Group means and standard deviations
  - Cohen's d effect size
  - Cronbach's alpha (internal consistency) for both scales
"""

import os
import pandas as pd
import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.path.join(SCRIPT_DIR, '..', 'data', 'responses.csv')
df = pd.read_csv(DATA_PATH)


# ---------------------------------------------------------------------------
# 2. Per-participant scale means
# ---------------------------------------------------------------------------
LIK_ITEMS = ['G1', 'G2', 'G3', 'G4', 'G5']
PES_ITEMS = ['P1', 'P2', 'P3', 'P4', 'P5']

df['Likability_Avg'] = df[LIK_ITEMS].mean(axis=1)
df['Empathy_Avg']    = df[PES_ITEMS].mean(axis=1)

emp = df[df['Condition'] == 'Empathetic']
neu = df[df['Condition'] == 'Neutral']


# ---------------------------------------------------------------------------
# 3. Helpers
# ---------------------------------------------------------------------------
def cohens_d(a, b):
    a, b = np.asarray(a), np.asarray(b)
    na, nb = len(a), len(b)
    var_a, var_b = a.var(ddof=1), b.var(ddof=1)
    pooled = np.sqrt(((na - 1) * var_a + (nb - 1) * var_b) / (na + nb - 2))
    return (a.mean() - b.mean()) / pooled


def cronbach_alpha(items):
    items = np.asarray(items, dtype=float)
    k = items.shape[1]
    item_var  = items.var(axis=0, ddof=1).sum()
    total_var = items.sum(axis=1).var(ddof=1)
    return (k / (k - 1)) * (1 - item_var / total_var)


def pct(mean):
    return mean / 5.0 * 100.0


# ---------------------------------------------------------------------------
# 4. Compute statistics
# ---------------------------------------------------------------------------
t_emp, p_emp = stats.ttest_ind(emp['Empathy_Avg'],    neu['Empathy_Avg'])
t_lik, p_lik = stats.ttest_ind(emp['Likability_Avg'], neu['Likability_Avg'])

d_emp = cohens_d(emp['Empathy_Avg'],    neu['Empathy_Avg'])
d_lik = cohens_d(emp['Likability_Avg'], neu['Likability_Avg'])

alpha_lik = cronbach_alpha(df[LIK_ITEMS].values)
alpha_pes = cronbach_alpha(df[PES_ITEMS].values)


# ---------------------------------------------------------------------------
# 5. Print results
# ---------------------------------------------------------------------------
lines = []
lines.append("=== Perceived Empathy (PES) ===")
lines.append(f"  Empathetic: M={emp['Empathy_Avg'].mean():.2f}  SD={emp['Empathy_Avg'].std(ddof=1):.2f}  ({pct(emp['Empathy_Avg'].mean()):.1f}%)")
lines.append(f"  Neutral:    M={neu['Empathy_Avg'].mean():.2f}  SD={neu['Empathy_Avg'].std(ddof=1):.2f}  ({pct(neu['Empathy_Avg'].mean()):.1f}%)")
lines.append(f"  t(22)={t_emp:.2f}, p={p_emp:.4f}, Cohen's d={d_emp:.2f}")
lines.append("")
lines.append("=== Likability (Godspeed) ===")
lines.append(f"  Empathetic: M={emp['Likability_Avg'].mean():.2f}  SD={emp['Likability_Avg'].std(ddof=1):.2f}  ({pct(emp['Likability_Avg'].mean()):.1f}%)")
lines.append(f"  Neutral:    M={neu['Likability_Avg'].mean():.2f}  SD={neu['Likability_Avg'].std(ddof=1):.2f}  ({pct(neu['Likability_Avg'].mean()):.1f}%)")
lines.append(f"  t(22)={t_lik:.2f}, p={p_lik:.4f}, Cohen's d={d_lik:.2f}")
lines.append("")
lines.append("=== Internal Consistency (Cronbach's alpha) ===")
lines.append(f"  Godspeed Likability (5 items): alpha={alpha_lik:.3f}")
lines.append(f"  PES                 (5 items): alpha={alpha_pes:.3f}")

print("\n".join(lines))

# end of file
