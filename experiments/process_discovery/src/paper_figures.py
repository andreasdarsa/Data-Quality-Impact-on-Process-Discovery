"""
Figures, tables and summary statistics for the process discovery section of the paper.

Inputs (run these first, from the project root):
    dual_log_analysis.py       -> results/dual_log_analysis/{cells,instances}.csv
    degradation_mechanisms.py  -> results/paper/degradation_mechanisms.csv

Outputs in results/paper/:
    fig_dual_evaluation_30.pdf   observed vs reference change at rho = 0.3
    fig_gap_by_level.pdf         aggregate score change by level, with run ranges
    tab_mechanisms.tex           log-level effects of each operator at rho = 0.3
    tab_complexity.tex           structural change at rho = 0.3 by sample size
    paper_stats.txt              numbers quoted in the text
"""
from pathlib import Path
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from config import RESULTS_DIR


DIMENSIONS = ["accuracy", "completeness", "consistency", "timeliness"]
MINERS = ["alpha", "heuristics", "inductive"]
MEASURES = ["fitness", "precision", "generalization", "average_score"]
MEASURE_LABEL = {
    "fitness": "Fitness",
    "precision": "Precision",
    "generalization": "Generalisation",
    "average_score": "Aggregate score",
}
# Logs evaluated at both sample sizes, used for the 1,000 vs 2,000 comparison.
PAIRED_LOGS = ["BPI 2019", "BPI 2020 Domestic", "BPI 2017", "BPI 2012"]

# Validated categorical pair (blue / orange); markers differ as well, for greyscale print.
OBS = {"color": "#2a78d6", "marker": "o", "label": r"Degraded log ($\Delta_{\mathrm{obs}}$)"}
REF = {"color": "#eb6834", "marker": "s", "label": r"Reference log ($\Delta_{\mathrm{ref}}$)"}
INK, INK_2, RULE = "#161a22", "#4a5263", "#cfd4dc"

TEXTWIDTH_IN = 122 / 25.4  # LNCS text width

plt.rcParams.update(
    {
        "font.family": "serif",
        # Times-compatible TrueType face, so the fonts embed cleanly (pdf.fonttype 42).
        "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 7.5,
        "axes.titlesize": 8,
        "axes.labelsize": 7.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "axes.edgecolor": INK_2,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.color": INK_2,
        "ytick.color": INK,
        "axes.labelcolor": INK,
        "text.color": INK,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    }
)


def run_means(cells: pd.DataFrame) -> pd.DataFrame:
    """Per run x dimension x level: mean over miners (repetitions already averaged in cells)."""
    return cells.groupby(["run", "log", "sample_size", "dimension", "degradation_level"], as_index=False).mean(numeric_only=True)


def overall_means(cells: pd.DataFrame) -> pd.DataFrame:
    """Per dimension x level: mean over runs and miners, each run weighted equally."""
    return cells.groupby(["dimension", "degradation_level"]).mean(numeric_only=True)


def footer(fig, xlabel: str, handles: list, y: float) -> None:
    """Axis title (left) and legend (right) on one row below the panels, to save vertical space."""
    fig.text(0.1, y, xlabel, ha="left", va="center", fontsize=7.5, color=INK)
    fig.legend(handles=handles, loc="center right", ncol=2, frameon=False, bbox_to_anchor=(0.995, y), handletextpad=0.3, columnspacing=1.2, borderaxespad=0)


def figure_dual_evaluation(cells: pd.DataFrame, path: Path) -> None:
    means = overall_means(cells).xs(30, level="degradation_level")

    fig, axes = plt.subplots(1, 4, figsize=(TEXTWIDTH_IN, 1.18), sharey=True, sharex=True)
    y = np.arange(len(DIMENSIONS))[::-1]

    for ax, measure in zip(axes, MEASURES):
        d_obs = means.loc[DIMENSIONS, f"{measure}_delta_obs"].to_numpy()
        d_ref = means.loc[DIMENSIONS, f"{measure}_delta_ref"].to_numpy()

        ax.axvline(0, color=INK_2, linewidth=0.7, zorder=1)
        ax.hlines(y, np.minimum(d_obs, d_ref), np.maximum(d_obs, d_ref), color="#9aa2b2", linewidth=1.4, zorder=2)
        for spec, values in ((REF, d_ref), (OBS, d_obs)):
            ax.scatter(values, y, s=18, color=spec["color"], marker=spec["marker"], edgecolor="white", linewidth=0.6, zorder=3)

        ax.set_title(MEASURE_LABEL[measure], pad=2)
        ax.set_xlim(-0.62, 0.32)
        ax.set_xticks([-0.4, 0, 0.2])
        ax.set_xticks([-0.6, -0.2], minor=True)
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:+.1f}".replace("-", "−") if abs(v) > 1e-9 else "0")
        ax.tick_params(axis="x", which="minor", length=2)
        ax.grid(axis="x", which="both", color=RULE, linewidth=0.5, zorder=0)
        ax.tick_params(axis="y", length=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)

    axes[0].set_yticks(y)
    axes[0].set_yticklabels([d.capitalize() for d in DIMENSIONS])
    axes[0].set_ylim(-0.45, len(DIMENSIONS) - 0.55)

    handles = [
        Line2D([], [], linestyle="none", marker=s["marker"], color=s["color"], markeredgecolor="white", markersize=5, label=s["label"])
        for s in (OBS, REF)
    ]
    footer(fig, r"Change relative to the baseline, $q - q_0$ ($\rho = 0.3$)", handles, y=-0.16)
    fig.subplots_adjust(wspace=0.08)
    fig.savefig(path)
    plt.close(fig)


def figure_gap_by_level(cells: pd.DataFrame, path: Path) -> None:
    per_run = run_means(cells)
    levels = [0, 10, 20, 30]
    x = [l / 100 for l in levels]

    fig, axes = plt.subplots(1, 4, figsize=(TEXTWIDTH_IN, 1.15), sharey=True)
    for ax, dim in zip(axes, DIMENSIONS):
        part = per_run[per_run["dimension"] == dim]
        for spec, col in ((OBS, "average_score_delta_obs"), (REF, "average_score_delta_ref")):
            stats = part.groupby("degradation_level")[col].agg(["mean", "min", "max"]).reindex([10, 20, 30])
            mean = np.r_[0, stats["mean"]]
            lo = np.r_[0, stats["min"]]
            hi = np.r_[0, stats["max"]]
            ax.fill_between(x, lo, hi, color=spec["color"], alpha=0.16, linewidth=0)
            ax.plot(x, mean, color=spec["color"], linewidth=1.3, marker=spec["marker"], markersize=3.6, markeredgecolor="white", markeredgewidth=0.5)

        ax.axhline(0, color=INK_2, linewidth=0.6)
        ax.set_title(dim.capitalize(), pad=2)
        ax.set_xticks(x)
        ax.set_xticklabels(["0", "0.1", "0.2", "0.3"])
        ax.set_xlim(-0.02, 0.32)
        ax.grid(axis="y", color=RULE, linewidth=0.5)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    axes[0].set_ylabel(r"$\Delta$ aggregate score")
    axes[0].set_yticks([0, -0.1, -0.2, -0.3])
    axes[0].yaxis.set_major_formatter(lambda v, _: f"{v:+.1f}".replace("-", "−") if abs(v) > 1e-9 else "0")
    handles = [
        Line2D([], [], color=s["color"], marker=s["marker"], markersize=4, markeredgecolor="white", linewidth=1.3, label=s["label"])
        for s in (OBS, REF)
    ]
    footer(fig, r"Degradation level $\rho$", handles, y=-0.17)
    fig.subplots_adjust(wspace=0.08)
    fig.savefig(path)
    plt.close(fig)


def fmt_pct(v: float) -> str:
    s = f"{v:+.0f}" if abs(v) >= 0.5 else "0"
    return s.replace("-", "$-$").replace("+", "$+$")


def fmt_share(v: float) -> str:
    return f"{100 * v:.0f}"


def table_mechanisms(mech: pd.DataFrame, path: Path) -> pd.DataFrame:
    cols = ["pct_activities", "pct_df_relations", "novel_df_share", "lost_df_share", "pct_variants", "pct_mean_length", "changed_case_share"]
    per_run = mech.groupby(["run", "dimension", "degradation_level"])[cols].mean()
    table = per_run.xs(30, level="degradation_level").groupby("dimension").mean().reindex(DIMENSIONS)

    rows = []
    for dim, r in table.iterrows():
        rows.append(
            f"{dim.capitalize()} & {fmt_pct(r.pct_activities)} & {fmt_pct(r.pct_df_relations)} & {fmt_share(r.novel_df_share)} & "
            f"{fmt_share(r.lost_df_share)} & {fmt_pct(r.pct_variants)} & {fmt_pct(r.pct_mean_length)} & {fmt_share(r.changed_case_share)} \\\\"
        )

    latex = r"""\begin{table}[t]
\caption{Effect of each operator on the event log itself at $\rho=0.3$, relative to $L_0$: change in the number of activities, distinct directly-follows (DF) relations, variants and mean trace length; share of DF relations of $L_{d,\rho,r}$ absent from $L_0$ (\emph{novel}) and of $L_0$ relations no longer observed (\emph{lost}); share of reference cases whose activity sequence differs (\emph{changed}). All values in \%; means over configurations and repetitions.}
\label{tab:mechanisms}
\centering\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lrrrrrrr@{}}
\toprule
 & \multicolumn{2}{c}{\textbf{Change}} & \multicolumn{2}{c}{\textbf{DF share}} & \multicolumn{3}{c}{\textbf{Traces}} \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(l){6-8}
\textbf{Dimension} & \textbf{Acts.} & \textbf{DF} & \textbf{Novel} & \textbf{Lost} & \textbf{Variants} & \textbf{Length} & \textbf{Changed} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    path.write_text(latex)
    return table


def table_complexity(cells: pd.DataFrame, path: Path) -> pd.DataFrame:
    c30 = cells[cells["degradation_level"] == 30]
    paired = c30[c30["log"].isin(PAIRED_LOGS)]

    def mean_by(df, col):
        # Mean over miners within each run first, then over runs.
        return df.groupby(["run", "dimension"])[col].mean().groupby("dimension").mean().reindex(DIMENSIONS)

    out = pd.DataFrame(index=DIMENSIONS)
    for col, name in (("transitions_pct_change", "trans"), ("arcs_pct_change", "arcs")):
        for n in (1000, 2000):
            out[f"{name}_{n}"] = mean_by(paired[paired["sample_size"] == n], col)
        out[f"{name}_all"] = mean_by(c30, col)
        per_run = c30.groupby(["run", "dimension"])[col].mean().unstack("dimension")
        out[f"{name}_min"] = per_run.min().reindex(DIMENSIONS)
        out[f"{name}_max"] = per_run.max().reindex(DIMENSIONS)

    rows = []
    for dim, r in out.iterrows():
        rows.append(
            f"{dim.capitalize()} & {fmt_pct(r.trans_1000)} & {fmt_pct(r.trans_2000)} & {fmt_pct(r.trans_all)} & "
            f"{fmt_pct(r.arcs_1000)} & {fmt_pct(r.arcs_2000)} & {fmt_pct(r.arcs_all)} & [{r.arcs_min:.0f}, {r.arcs_max:.0f}] \\\\"
        )

    latex = r"""\begin{table}[t]
\caption{Change in the number of transitions and arcs of the discovered Petri nets at $\rho=0.3$, relative to $M_0$ (\%). The 1,000- and 2,000-case columns cover the four logs prepared at both sizes; \emph{All} covers all nine configurations, with the range of per-configuration means. Means over miners and repetitions.}
\label{tab:complexity}
\centering\footnotesize
\setlength{\tabcolsep}{4.5pt}
\begin{tabular}{@{}lrrrrrrr@{}}
\toprule
 & \multicolumn{3}{c}{\textbf{Transitions}} & \multicolumn{4}{c}{\textbf{Arcs}} \\
\cmidrule(lr){2-4}\cmidrule(l){5-8}
\textbf{Dimension} & \textbf{1,000} & \textbf{2,000} & \textbf{All} & \textbf{1,000} & \textbf{2,000} & \textbf{All} & \textbf{Range} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    path.write_text(latex)
    return out


def sample_size_agreement(cells: pd.DataFrame) -> pd.Series:
    """Pearson correlation between 1,000- and 2,000-case cell means for the paired logs."""
    keys = ["log", "dimension", "degradation_level", "miner"]
    paired = cells[cells["log"].isin(PAIRED_LOGS)]
    merged = paired[paired["sample_size"] == 1000].merge(paired[paired["sample_size"] == 2000], on=keys, suffixes=("_1000", "_2000"))
    cols = [
        "average_score_delta_obs", "average_score_delta_ref", "average_score_gap",
        "precision_gap", "generalization_gap", "fitness_gap",
        "transitions_pct_change", "arcs_pct_change",
    ]
    return pd.Series({c: merged[f"{c}_1000"].corr(merged[f"{c}_2000"]) for c in cols}).round(3)


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--analysis-dir", default=f"{RESULTS_DIR}/dual_log_analysis")
    parser.add_argument("--output-dir", default=f"{RESULTS_DIR}/paper")
    args = parser.parse_args()

    analysis_dir = Path(args.analysis_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cells = pd.read_csv(analysis_dir / "cells.csv")
    instances = pd.read_csv(analysis_dir / "instances.csv")
    mechanisms = pd.read_csv(output_dir / "degradation_mechanisms.csv")

    figure_dual_evaluation(cells, output_dir / "fig_dual_evaluation_30.pdf")
    figure_gap_by_level(cells, output_dir / "fig_gap_by_level.pdf")
    mech_table = table_mechanisms(mechanisms, output_dir / "tab_mechanisms.tex")
    complexity = table_complexity(cells, output_dir / "tab_complexity.tex")

    # Numbers quoted in the text.
    tol = 0.02
    concealed = (instances["average_score_delta_obs"] >= -tol) & (instances["average_score_delta_ref"] < -tol)
    lines = [
        f"models: {len(instances)}, configurations: {instances['run'].nunique()}",
        f"share aggregate gap > {tol}: {(instances['average_score_gap'] > tol).mean():.3f}",
        f"share precision gap > {tol}: {(instances['precision_gap'] > tol).mean():.3f}",
        f"share concealed (aggregate): {concealed.mean():.3f}; excluding alpha: {concealed[instances['miner'] != 'alpha'].mean():.3f}",
        "",
        "Means at 30% (dimension x measure):",
        overall_means(cells).xs(30, level="degradation_level")[[f"{m}_{k}" for m in MEASURES for k in ("delta_obs", "delta_ref", "gap")]].round(3).T.to_string(),
        "",
        "Per-configuration aggregate change at 30% (min, max over the 8 configurations):",
        run_means(cells).query("degradation_level == 30").groupby("dimension")[["average_score_delta_obs", "average_score_delta_ref", "average_score_gap"]].agg(["min", "max"]).round(3).to_string(),
        "",
        "Log-level mechanisms at 30%:",
        mech_table.round(3).to_string(),
        "",
        "Structural change at 30%:",
        complexity.round(1).to_string(),
        "",
        "Agreement between 1,000 and 2,000 cases (Pearson r over dimension x level x miner cells):",
        sample_size_agreement(cells).to_string(),
    ]
    (output_dir / "paper_stats.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nSaved figures and tables to {output_dir}")


if __name__ == "__main__":
    main()
