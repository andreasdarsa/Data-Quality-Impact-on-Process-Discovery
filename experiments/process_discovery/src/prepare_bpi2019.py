from pathlib import Path
import argparse
import pandas as pd
import pm4py

from config import RAW_LOG_PATH, PREPARED_DIR


def prepare_bpi2019(
    input_path: str,
    output_path: str,
    max_cases: int = 1000,
    random_state: int = 42,
):
    print(f"Reading BPI 2019 log from: {input_path}")

    log = pm4py.read_xes(input_path)
    df = pm4py.convert_to_dataframe(log)

    print("\nOriginal columns:")
    for col in df.columns:
        print(f"- {col}")

    required_cols = [
        "case:concept:name",
        "concept:name",
        "time:timestamp",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

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
    )

    initial_events = len(df)
    initial_cases = df["case_id"].nunique()
    initial_activities = df["activity"].nunique()

    df = df.dropna(
        subset=[
            "case_id",
            "activity",
            "complete_timestamp",
        ]
    )

    # Κρατάμε τη σειρά των events μέσα σε κάθε case όπως εμφανίζεται στο XES.
    df["event_index"] = df.groupby("case_id").cumcount()

    useful_optional_cols = [
        "org:resource",
        "case:Purchasing Document",
        "case:Item",
        "case:Item Type",
        "case:Goods Receipt",
        "case:GR-Based Inv. Verif.",
        "case:Document Type",
        "case:Item Category",
        "case:Spend area text",
        "case:Sub spend area text",
        "case:Company",
        "case:Vendor",
        "case:Name",
    ]

    keep_cols = [
        "case_id",
        "activity",
        "complete_timestamp",
        "event_index",
    ]

    keep_cols += [col for col in useful_optional_cols if col in df.columns]

    df = df[keep_cols].copy()

    all_cases = pd.Series(df["case_id"].unique())

    if max_cases is not None and max_cases < len(all_cases):
        sampled_cases = all_cases.sample(
            n=max_cases,
            random_state=random_state,
        )

        df = df[df["case_id"].isin(sampled_cases)].copy()

    df = df.sort_values(
        by=[
            "case_id",
            "complete_timestamp",
            "event_index",
        ]
    ).reset_index(drop=True)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)

    print("\nPrepared log saved.")
    print(f"Output path: {output_path}")

    print("\nOriginal log:")
    print(f"Events: {initial_events}")
    print(f"Cases: {initial_cases}")
    print(f"Activities: {initial_activities}")

    print("\nPrepared subset:")
    print(f"Events: {len(df)}")
    print(f"Cases: {df['case_id'].nunique()}")
    print(f"Activities: {df['activity'].nunique()}")

    print("\nActivity distribution:")
    print(df["activity"].value_counts())


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default=RAW_LOG_PATH,
        help="Path to BPI 2019 .xes file",
    )

    parser.add_argument(
        "--output",
        default=f"{PREPARED_DIR}/bpi2019_baseline_1000_cases.csv",
        help="Output CSV path",
    )

    parser.add_argument(
        "--max-cases",
        type=int,
        default=1000,
        help="Maximum number of cases to keep",
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducible sampling",
    )

    args = parser.parse_args()

    prepare_bpi2019(
        input_path=args.input,
        output_path=args.output,
        max_cases=args.max_cases,
        random_state=args.random_state,
    )


if __name__ == "__main__":
    main()
