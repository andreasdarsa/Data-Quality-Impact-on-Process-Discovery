from pathlib import Path
import argparse

import pandas as pd
import matplotlib.pyplot as plt

from config import (
    METRICS_DIR,
    FIGURES_DIR,
    DEGRADATION_DIMENSIONS,
)


QUALITY_METRICS = [
    "fitness",
    "precision",
    "generalization",
    "simplicity",
    "average_score",
]

STRUCTURAL_METRICS = [
    "places",
    "transitions",
    "visible_transitions",
    "hidden_transitions",
    "arcs",
    "unique_visible_transition_labels",
    "duplicate_visible_transition_labels",
]


def load_results(input_path: str) -> pd.DataFrame:
    df = pd.read_csv(input_path)

    if "status" in df.columns:
        df = df[df["status"] == "ok"].copy()

    numeric_cols = [
        "degradation_level",
        *QUALITY_METRICS,
        *STRUCTURAL_METRICS,
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def add_baseline_to_each_dimension(
    df: pd.DataFrame,
    dimensions: list[str],
) -> pd.DataFrame:
    """
    Copies baseline rows to every degradation dimension.

    This allows plots to show:
        0%, 10%, 20%, 30%

    for each dimension.
    """
    baseline_df = df[df["dimension"] == "baseline"].copy()
    degraded_df = df[df["dimension"] != "baseline"].copy()

    if baseline_df.empty:
        return degraded_df

    expanded_baseline_rows = []

    for dimension in dimensions:
        temp = baseline_df.copy()
        temp["dimension"] = dimension
        temp["degradation_level"] = 0
        temp["repetition"] = 0
        expanded_baseline_rows.append(temp)

    expanded_baseline_df = pd.concat(
        expanded_baseline_rows,
        ignore_index=True,
    )

    return pd.concat(
        [expanded_baseline_df, degraded_df],
        ignore_index=True,
    )


def aggregate_results(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates repetitions by mean.

    Grouping:
        dimension, degradation_level, miner
    """
    metric_cols = [
        col
        for col in QUALITY_METRICS + STRUCTURAL_METRICS
        if col in df.columns
    ]

    grouped = (
        df.groupby(
            [
                "dimension",
                "degradation_level",
                "miner",
            ],
            as_index=False,
        )[metric_cols]
        .mean()
    )

    return grouped


def plot_metric_for_dimension(
    df: pd.DataFrame,
    metric: str,
    dimension: str,
    output_dir: str,
) -> None:
    """
    Creates one plot for one metric and one degradation dimension.
    """
    dimension_df = df[df["dimension"] == dimension].copy()

    if dimension_df.empty or metric not in dimension_df.columns:
        return

    output_path = Path(output_dir) / f"{metric}_by_{dimension}.png"

    plt.figure(figsize=(9, 5))

    for miner_name, miner_df in dimension_df.groupby("miner"):
        miner_df = miner_df.sort_values("degradation_level")

        plt.plot(
            miner_df["degradation_level"],
            miner_df[metric],
            marker="o",
            label=miner_name,
        )

    plt.title(f"{metric.replace('_', ' ').title()} by degradation level - {dimension}")
    plt.xlabel("Degradation level (%)")
    plt.ylabel(metric.replace("_", " ").title())
    plt.xticks([0, 10, 20, 30])
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()

    print(f"Saved plot: {output_path}")


def plot_all_metrics(
    df: pd.DataFrame,
    output_dir: str,
    dimensions: list[str],
) -> None:
    """
    Creates one plot per metric per dimension.
    """
    available_metrics = [
        metric
        for metric in QUALITY_METRICS + STRUCTURAL_METRICS
        if metric in df.columns
    ]

    for dimension in dimensions:
        for metric in available_metrics:
            plot_metric_for_dimension(
                df=df,
                metric=metric,
                dimension=dimension,
                output_dir=output_dir,
            )


def save_aggregated_results(
    df: pd.DataFrame,
    output_dir: str,
) -> None:
    output_path = Path(output_dir) / "aggregated_results.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)

    print(f"Saved aggregated results: {output_path}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default=f"{METRICS_DIR}/discovery_results.csv",
        help="Path to discovery_results.csv.",
    )

    parser.add_argument(
        "--output-dir",
        default=FIGURES_DIR,
        help="Directory where plots will be saved.",
    )

    parser.add_argument(
        "--dimensions",
        nargs="+",
        default=None,
        help="Dimensions to plot.",
    )

    args = parser.parse_args()

    dimensions = args.dimensions or DEGRADATION_DIMENSIONS

    raw_df = load_results(args.input)

    plot_ready_df = add_baseline_to_each_dimension(
        df=raw_df,
        dimensions=dimensions,
    )

    aggregated_df = aggregate_results(plot_ready_df)

    save_aggregated_results(
        df=aggregated_df,
        output_dir=Path(args.output_dir).parent / "metrics",
    )

    plot_all_metrics(
        df=aggregated_df,
        output_dir=args.output_dir,
        dimensions=dimensions,
    )


if __name__ == "__main__":
    main()
