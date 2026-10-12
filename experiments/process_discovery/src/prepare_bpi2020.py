# Extractor for the BPI Challenge 2020 Dataset (Travel Permit Process)
from pathlib import Path
import argparse

import pandas as pd
import pm4py


def prepare_bpi2020(
    input_path: str,
    output_path: str,
    max_cases: int = 1000,
    random_state: int = 42,
):
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input XES not found: {input_path}")

    print(f"Reading BPI 2020 Travel Permit log: {input_path}")

    log = pm4py.read_xes(str(input_path))
    df = pm4py.convert_to_dataframe(log)

    print("\nOriginal columns:")
    for col in df.columns:
        print(f"- {col}")

    required_cols = [
        "case:concept:name",
        "concept:name",
        "time:timestamp",
    ]

    missing_cols = [
        col for col in required_cols if col not in df.columns
    ]

    if missing_cols:
        raise ValueError(
            f"Missing required columns: {missing_cols}"
        )

    df = df.rename(
        columns={
            "case:concept:name": "case_id",
            "concept:name": "activity",
            "time:timestamp": "complete_timestamp",
        }
    )

    df["complete_timestamp"] = pd.to_datetime(
        df["complete_timestamp"],
        errors="coerce",
        utc=True,
    )

    original_events = len(df)
    original_cases = df["case_id"].nunique()
    original_activities = df["activity"].nunique()

    df = df.dropna(
        subset=[
            "case_id",
            "activity",
            "complete_timestamp",
        ]
    ).copy()

    valid_cases = df["case_id"].unique()

    if max_cases is not None:
        if max_cases <= 0:
            raise ValueError("max_cases must be positive or None")

        n_cases = min(max_cases, len(valid_cases))

        sampled_cases = pd.Series(valid_cases).sample(
            n=n_cases,
            random_state=random_state,
        )

        df = df[df["case_id"].isin(sampled_cases)].copy()

    df = df.sort_values(
        ["case_id", "complete_timestamp"],
        kind="stable",
    ).reset_index(drop=True)

    df["event_index"] = (
        df.groupby("case_id").cumcount()
    )

    df = df[
        [
            "case_id",
            "activity",
            "complete_timestamp",
            "event_index",
        ]
    ]

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(output_path, index=False)

    print("\nOriginal log:")
    print(f"Events: {original_events}")
    print(f"Cases: {original_cases}")
    print(f"Activities: {original_activities}")

    print("\nPrepared subset:")
    print(f"Events: {len(df)}")
    print(f"Cases: {df['case_id'].nunique()}")
    print(f"Activities: {df['activity'].nunique()}")
    print(f"Timestamp range: {df['complete_timestamp'].min()} "
          f"to {df['complete_timestamp'].max()}")
    print(f"\nSaved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Prepare BPI 2020 Travel Permit event log."
    )

    parser.add_argument(
        "--input",
        default="data/raw/bpi2020/PermitLog.xes",
        help="Path to the original XES file",
    )

    parser.add_argument(
        "--output",
        default=(
            "data/prepared/"
            "bpi2020_travel_permit_baseline_1000_cases.csv"
        ),
        help="Path to the prepared CSV",
    )

    parser.add_argument(
        "--max-cases",
        type=int,
        default=1000,
        help="Number of cases to sample; use 0 for all cases",
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducible sampling",
    )

    args = parser.parse_args()

    prepare_bpi2020(
        input_path=args.input,
        output_path=args.output,
        max_cases=None if args.max_cases == 0 else args.max_cases,
        random_state=args.random_state,
    )


if __name__ == "__main__":
    main()
