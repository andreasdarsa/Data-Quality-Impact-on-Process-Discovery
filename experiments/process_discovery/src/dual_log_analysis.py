"""
Dual-log analysis of process discovery under data-quality degradation.

For a discovery algorithm A, M_0 = A(L_0) is the baseline model and
M_{d,rho,r} = A(L_{d,rho,r}) the model discovered from a degraded log.
For every log-dependent measure q (fitness, precision, generalization):

    q_0   = q(M_0, L_0)
    q_obs = q(M_{d,rho,r}, L_{d,rho,r})    (discovery_results_with_fitness.csv)
    q_ref = q(M_{d,rho,r}, L_0)            (discovery_results_vs_original_with_fitness.csv)

    delta_obs = q_obs - q_0,  delta_ref = q_ref - q_0,  gap = q_obs - q_ref

Simplicity and the structural measures depend only on the model, so they are
compared directly between M_{d,rho,r} and M_0.
"""
from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from config import RESULTS_DIR


# (log label, sample size, results folder). The BPI 2019 models were
# rediscovered under rerun_bpi2019_*, so both of their evaluations use the
# same models.
RUNS = [
    ("BPI 2019", 1000, "rerun_bpi2019_1000"),
    ("BPI 2019", 2000, "rerun_bpi2019_2000"),
    ("BPI 2020 Domestic", 1000, "bpi2020_domestic_declarations_1000"),
    ("BPI 2020 Domestic", 2000, "bpi2020_domestic_declarations_2000"),
    ("BPI 2017", 1000, "bpi2017_1000"),
    ("BPI 2017", 2000, "bpi2017_2000"),
    ("BPI 2012", 1000, "bpi2012_1000"),
    ("BPI 2012", 2000, "bpi2012_2000"),
    ("Sepsis", 1000, "sepsis_1000"),
]

LOG_DEPENDENT = ["fitness", "precision", "generalization"]
MODEL_ONLY = ["simplicity"]
STRUCTURAL = ["places", "transitions", "arcs"]

# The aggregate quality score is the mean of the four measures. Its gap equals
# the mean of the three log-dependent gaps, since simplicity does not depend
# on the log.
AGGREGATE = "average_score"

KEYS = ["dimension", "degradation_level", "repetition", "miner"]
DIMENSIONS = ["accuracy", "completeness", "consistency", "timeliness"]
MINERS = ["alpha", "heuristics", "inductive"]

# Changes smaller than this are treated as no change when classifying
# instances. It is above the largest difference observed when the same model
# is evaluated twice on the same log (Heuristics Miner replay, about 0.013).
TOLERANCE = 0.02


def load_results(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["status"] == "ok"].copy()
    df["fitness"] = pd.to_numeric(df["fitness_reconstructed"], errors="coerce")
    return df


def build_instances(results_dir: Path, runs=RUNS) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns one row per degraded model (run x dimension x level x repetition x
    miner) with all q_0, q_obs, q_ref values and derived changes, a table of
    baseline sanity checks, and one row per run describing its baseline log.
    """
    instances = []
    checks = []
    run_info = []

    for log_name, n_cases, folder in runs:
        metrics_dir = results_dir / folder / "metrics"
        obs_path = metrics_dir / "discovery_results_with_fitness.csv"
        ref_path = metrics_dir / "discovery_results_vs_original_with_fitness.csv"

        if not (obs_path.exists() and ref_path.exists()):
            print(f"Skipping {log_name} {n_cases}: missing {obs_path.name} or {ref_path.name}")
            continue

        obs = load_results(obs_path)
        ref = load_results(ref_path)

        quality = LOG_DEPENDENT + MODEL_ONLY + [AGGREGATE]

        baseline = obs[obs["dimension"] == "baseline"].set_index("miner")[quality + STRUCTURAL]
        baseline_ref = ref[ref["dimension"] == "baseline"].set_index("miner")[quality]

        # q(M_0, L_0) is computed in both files; any difference is evaluation noise.
        for miner in baseline.index:
            for q in quality:
                checks.append(
                    {
                        "log": log_name,
                        "sample_size": n_cases,
                        "miner": miner,
                        "measure": q,
                        "abs_diff": abs(baseline.at[miner, q] - baseline_ref.at[miner, q]),
                    }
                )

        degraded = obs[obs["dimension"] != "baseline"][KEYS + quality + STRUCTURAL + ["activities_after"]].merge(
            ref[ref["dimension"] != "baseline"][KEYS + quality],
            on=KEYS,
            suffixes=("_obs", "_ref"),
            validate="one_to_one",
        )

        base = baseline.reindex(degraded["miner"]).reset_index(drop=True)

        degraded["log"] = log_name
        degraded["sample_size"] = n_cases
        degraded["run"] = f"{log_name} ({n_cases})"

        for q in LOG_DEPENDENT + [AGGREGATE]:
            degraded[f"{q}_0"] = base[q].to_numpy()
            degraded[f"{q}_delta_obs"] = degraded[f"{q}_obs"] - degraded[f"{q}_0"]
            degraded[f"{q}_delta_ref"] = degraded[f"{q}_ref"] - degraded[f"{q}_0"]
            degraded[f"{q}_gap"] = degraded[f"{q}_obs"] - degraded[f"{q}_ref"]

        for q in MODEL_ONLY:
            degraded[f"{q}_0"] = base[q].to_numpy()
            degraded[f"{q}_delta"] = degraded[f"{q}_obs"] - degraded[f"{q}_0"]
            # Model-only: both evaluations must agree.
            degraded[f"{q}_obs_ref_diff"] = (degraded[f"{q}_obs"] - degraded[f"{q}_ref"]).abs()

        for s in STRUCTURAL:
            degraded[f"{s}_0"] = base[s].to_numpy()
            degraded[f"{s}_pct_change"] = 100 * (degraded[s] - degraded[f"{s}_0"]) / degraded[f"{s}_0"]

        instances.append(degraded)

        baseline_log = obs[obs["dimension"] == "baseline"].iloc[0]
        run_info.append(
            {
                "run": f"{log_name} ({n_cases})",
                "log": log_name,
                "sample_size": n_cases,
                "cases": int(baseline_log["cases_after"]),
                "events": int(baseline_log["events_after"]),
                "activities": int(baseline_log["activities_after"]),
                "repetitions": int(degraded["repetition"].max()),
                "degraded_models": len(degraded),
            }
        )

    if not instances:
        raise FileNotFoundError(
            f"No complete runs found under {results_dir.resolve()}. "
            "Run the script from the project root."
        )

    return pd.concat(instances, ignore_index=True), pd.DataFrame(checks), pd.DataFrame(run_info)


def cell_means(instances: pd.DataFrame) -> pd.DataFrame:
    """
    Averages repetitions, so that every run x dimension x level x miner cell has
    equal weight (the BPI 2019 run has 5 repetitions, the others 3).
    """
    numeric = instances.select_dtypes("number").columns.difference(["repetition", "sample_size", "degradation_level"])
    return (
        instances
        .groupby(["log", "sample_size", "run", "dimension", "degradation_level", "miner"], as_index=False)[list(numeric)]
        .mean()
    )


def summarize_quality_and_structure(cells: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """
    Perspective 1: changes of the discovered models relative to M_0, using the
    usual evaluation on the degraded log.
    """
    cols = {
        **{f"d_{q}_obs": (f"{q}_delta_obs", "mean") for q in LOG_DEPENDENT},
        "d_simplicity": ("simplicity_delta", "mean"),
        "d_average_obs": (f"{AGGREGATE}_delta_obs", "mean"),
        **{f"pct_{s}": (f"{s}_pct_change", "mean") for s in STRUCTURAL},
    }
    return cells.groupby(by).agg(**cols)


def summarize_dual_log(instances: pd.DataFrame, cells: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """
    Perspective 2: delta_obs, delta_ref and the evaluation gap per measure.

    Means are taken over repetition-averaged cells (equal weight per run).
    Shares are taken over individual model instances.
    """
    rows = []
    measures = LOG_DEPENDENT + [AGGREGATE]

    cell_groups = dict(list(cells.groupby(by)))
    for key, part in instances.groupby(by):
        cell_part = cell_groups[key]
        key = key if isinstance(key, tuple) else (key,)
        for q in measures:
            d_obs = part[f"{q}_delta_obs"]
            d_ref = part[f"{q}_delta_ref"]
            gap = part[f"{q}_gap"]
            rows.append(
                {
                    **dict(zip(by, key)),
                    "measure": q,
                    "delta_obs": cell_part[f"{q}_delta_obs"].mean(),
                    "delta_ref": cell_part[f"{q}_delta_ref"].mean(),
                    "gap": cell_part[f"{q}_gap"].mean(),
                    "gap_median": gap.median(),
                    "share_gap_positive": (gap > TOLERANCE).mean(),
                    "share_gap_negative": (gap < -TOLERANCE).mean(),
                    # Apparently stable or improved on the degraded log, but
                    # worse than the baseline on the reference log.
                    "share_concealed": ((d_obs >= -TOLERANCE) & (d_ref < -TOLERANCE)).mean(),
                    "n_instances": len(part),
                }
            )

    return pd.DataFrame(rows)


def runs_with_positive_gap(cells: pd.DataFrame, level: int) -> pd.DataFrame:
    """
    Number of runs whose mean gap (over miners and repetitions) is positive, per
    dimension and measure, at one degradation level.
    """
    part = cells[cells["degradation_level"] == level]
    per_run = part.groupby(["run", "dimension"])[[f"{q}_gap" for q in LOG_DEPENDENT + [AGGREGATE]]].mean()
    return (
        (per_run > TOLERANCE)
        .groupby("dimension").sum()
        .rename(columns=lambda c: c.removesuffix("_gap"))
        .assign(runs=per_run.groupby("dimension").size())
    )


def stable_but_more_complex(cells: pd.DataFrame) -> pd.DataFrame:
    """
    Share of cells whose aggregate score on the degraded log did not drop
    (delta >= -TOLERANCE) while the number of arcs grew by at least 10%.
    """
    flag = (cells[f"{AGGREGATE}_delta_obs"] >= -TOLERANCE) & (cells["arcs_pct_change"] >= 10)
    return (
        cells.assign(stable_but_more_complex=flag)
        .groupby(["dimension", "miner"])["stable_but_more_complex"]
        .mean()
        .unstack("miner")
        .reindex(DIMENSIONS)
    )


def write_latex(df: pd.DataFrame, path: Path, caption: str, label: str, float_format="%.3f") -> None:
    latex = df.to_latex(
        float_format=float_format,
        caption=caption,
        label=label,
        escape=True,
        multicolumn_format="c",
    )
    path.write_text(latex)


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--output-dir",
        default=f"{RESULTS_DIR}/dual_log_analysis",
        help="Folder for the CSV and LaTeX tables.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    instances, checks, run_info = build_instances(Path(RESULTS_DIR))
    cells = cell_means(instances)

    instances.to_csv(output_dir / "instances.csv", index=False)
    cells.to_csv(output_dir / "cells.csv", index=False)
    run_info.to_csv(output_dir / "runs.csv", index=False)

    # Sanity checks.
    print("Runs:", instances["run"].nunique(), "| model instances:", len(instances))
    print("Max |q(M_0,L_0) difference between the two evaluation files|:")
    print(checks.groupby(["miner", "measure"])["abs_diff"].max().unstack("measure").round(5))
    print("Max |simplicity_obs - simplicity_ref| (must be 0):", instances["simplicity_obs_ref_diff"].max())
    print("Max |generalization_obs - generalization_ref| (log dependence):",
          (instances["generalization_obs"] - instances["generalization_ref"]).abs().max().round(4))

    # Perspective 1.
    structure_by_level = summarize_quality_and_structure(cells, ["dimension", "degradation_level"])
    structure_by_miner_30 = summarize_quality_and_structure(
        cells[cells["degradation_level"] == 30], ["dimension", "miner"]
    )
    stable_complex = stable_but_more_complex(cells)

    # Perspective 2.
    dual_by_level = summarize_dual_log(instances, cells, ["dimension", "degradation_level"])
    dual_by_miner_30 = summarize_dual_log(
        instances[instances["degradation_level"] == 30],
        cells[cells["degradation_level"] == 30],
        ["dimension", "miner"],
    )
    dual_by_run_30 = summarize_dual_log(
        instances[instances["degradation_level"] == 30],
        cells[cells["degradation_level"] == 30],
        ["run", "dimension"],
    )
    positive_runs_30 = runs_with_positive_gap(cells, 30)

    tables = {
        "structure_by_level": structure_by_level,
        "structure_by_miner_30": structure_by_miner_30,
        "stable_but_more_complex": stable_complex,
        "dual_log_by_level": dual_by_level,
        "dual_log_by_miner_30": dual_by_miner_30,
        "dual_log_by_run_30": dual_by_run_30,
        "runs_with_positive_gap_30": positive_runs_30,
        "baseline_checks": checks,
    }
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=name not in {"dual_log_by_level", "dual_log_by_miner_30", "dual_log_by_run_30", "baseline_checks"})

    # LaTeX tables for the paper.
    gap_table = (
        dual_by_level[dual_by_level["measure"].isin(LOG_DEPENDENT)]
        .pivot_table(index=["dimension", "degradation_level"], columns="measure", values=["delta_obs", "delta_ref", "gap"])
        .swaplevel(axis=1)
        .reindex(columns=pd.MultiIndex.from_product([LOG_DEPENDENT, ["delta_obs", "delta_ref", "gap"]]))
    )
    write_latex(
        gap_table,
        output_dir / "dual_log_by_level.tex",
        caption=r"Changes relative to the baseline model, evaluated on the degraded log ($\Delta_{\mathrm{obs}}$) and on the reference log ($\Delta_{\mathrm{ref}}$), and the evaluation gap $G_q$. Means over runs, miners and repetitions.",
        label="tab:dual_log_by_level",
    )
    write_latex(
        structure_by_level,
        output_dir / "structure_by_level.tex",
        caption="Changes of the discovered models relative to the baseline model (quality on the degraded log, simplicity and structure). Structural changes in percent.",
        label="tab:structure_by_level",
        float_format="%.2f",
    )

    print(f"\nSaved tables to: {output_dir}")


if __name__ == "__main__":
    main()
