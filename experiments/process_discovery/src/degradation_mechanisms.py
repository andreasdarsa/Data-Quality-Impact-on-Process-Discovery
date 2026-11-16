"""
Log-level effects of each degradation operator, measured on the degraded logs
themselves (no discovery involved).

For every degraded log L_{d,rho,r} and its reference L_0 the script records the
number of activities, distinct directly-follows (DF) relations, variants and
trace length, the share of DF relations that do not occur in L_0 (novel), the
share of L_0 relations that disappear (lost), and the share of reference
cases whose activity sequence changed.
"""
from pathlib import Path
import argparse

import pandas as pd

from config import CASE_ID_COL, ACTIVITY_COL, COMPLETE_TIMESTAMP_COL, RESULTS_DIR


# (log label, sample size, degraded-log folder, prepared baseline file)
RUNS = [
    ("BPI 2019", 1000, "bpi2019_1000", "bpi2019_baseline_1000_cases.csv"),
    ("BPI 2019", 2000, "bpi2019_2000", "bpi2019_baseline_2000_cases.csv"),
    ("BPI 2020 Domestic", 1000, "bpi2020_domestic_declarations_1000", "bpi2020_domestic_declarations_baseline_1000_cases.csv"),
    ("BPI 2020 Domestic", 2000, "bpi2020_domestic_declarations_2000", "bpi2020_domestic_declarations_baseline_2000_cases.csv"),
    ("BPI 2017", 1000, "bpi2017_1000", "bpi2017_baseline_1000_cases.csv"),
    ("BPI 2017", 2000, "bpi2017_2000", "bpi2017_baseline_2000_cases.csv"),
    ("BPI 2012", 1000, "bpi2012_1000", "bpi2012_baseline_1000_cases.csv"),
    ("BPI 2012", 2000, "bpi2012_2000", "bpi2012_baseline_2000_cases.csv"),
    ("Sepsis", 1000, "sepsis_1000", "sepsis_baseline_1000_cases.csv"),
]


def read_traces(path: Path) -> dict:
    """
    Reads a prepared or degraded CSV and returns {case_id: tuple of activities},
    ordered as in the discovery experiment (timestamp, then event_index).
    """
    df = pd.read_csv(path, dtype={CASE_ID_COL: str}, keep_default_na=False, na_values=[""])
    df[COMPLETE_TIMESTAMP_COL] = pd.to_datetime(df[COMPLETE_TIMESTAMP_COL], errors="coerce", utc=True, format="ISO8601")
    df = df.dropna(subset=[CASE_ID_COL, ACTIVITY_COL, COMPLETE_TIMESTAMP_COL])

    if "event_index" not in df.columns:
        df["event_index"] = df.groupby(CASE_ID_COL).cumcount()

    df = df.sort_values([CASE_ID_COL, COMPLETE_TIMESTAMP_COL, "event_index"], kind="stable")
    return {case: tuple(acts) for case, acts in df.groupby(CASE_ID_COL, sort=False)[ACTIVITY_COL]}


def log_stats(traces: dict) -> dict:
    activities = set()
    df_relations = set()
    lengths = []

    for trace in traces.values():
        activities.update(trace)
        df_relations.update(zip(trace, trace[1:]))
        lengths.append(len(trace))

    return {
        "activities": activities,
        "df": df_relations,
        "variants": len(set(traces.values())),
        "mean_length": sum(lengths) / len(lengths),
    }


def compare(reference: dict, ref_stats: dict, degraded: dict) -> dict:
    deg_stats = log_stats(degraded)
    novel = deg_stats["df"] - ref_stats["df"]
    lost = ref_stats["df"] - deg_stats["df"]
    changed = sum(1 for case, trace in reference.items() if degraded.get(case) != trace)

    pct = lambda new, old: 100 * (new - old) / old

    return {
        "pct_activities": pct(len(deg_stats["activities"]), len(ref_stats["activities"])),
        "pct_df_relations": pct(len(deg_stats["df"]), len(ref_stats["df"])),
        "novel_df_share": len(novel) / len(deg_stats["df"]),
        "lost_df_share": len(lost) / len(ref_stats["df"]),
        "pct_variants": pct(deg_stats["variants"], ref_stats["variants"]),
        "pct_mean_length": pct(deg_stats["mean_length"], ref_stats["mean_length"]),
        "changed_case_share": changed / len(reference),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--degraded-dir", default="data/degraded")
    parser.add_argument("--prepared-dir", default="data/prepared")
    parser.add_argument("--output-dir", default=f"{RESULTS_DIR}/paper")
    args = parser.parse_args()

    rows = []
    for log_name, n_cases, folder, baseline_file in RUNS:
        reference = read_traces(Path(args.prepared_dir) / baseline_file)
        ref_stats = log_stats(reference)
        print(f"{log_name} ({n_cases}): {len(ref_stats['activities'])} activities, {len(ref_stats['df'])} DF relations, {ref_stats['variants']} variants")

        for path in sorted(Path(args.degraded_dir, folder).glob("*/*.csv")):
            dimension, level, repetition = path.stem.rsplit("_", 2)
            rows.append(
                {
                    "log": log_name,
                    "sample_size": n_cases,
                    "run": f"{log_name} ({n_cases})",
                    "dimension": dimension,
                    "degradation_level": int(level),
                    "repetition": int(repetition.lstrip("r")),
                    **compare(reference, ref_stats, read_traces(path)),
                }
            )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_dir / "degradation_mechanisms.csv", index=False)
    print(f"Saved {len(rows)} degraded logs to {output_dir / 'degradation_mechanisms.csv'}")


if __name__ == "__main__":
    main()
