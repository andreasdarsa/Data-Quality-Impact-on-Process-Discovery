# Generic extractor for XES event logs (BPI 2020 Domestic Declarations, Sepsis, BPI 2017, ...)
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET

import pandas as pd
import pm4py


STREAMING_EVENT_KEYS = [
    "concept:name",
    "time:timestamp",
    "lifecycle:transition",
]


def read_xes_streaming(input_path: Path) -> pd.DataFrame:
    """
    Reads only case id, activity, timestamp and lifecycle from an XES file.

    The file is parsed element by element, so memory use stays low even for
    very large logs (e.g. BPI 2018), where pm4py.read_xes would load every
    attribute of every event.
    """
    rows = []
    trace_events = []
    depth = 0

    for action, elem in ET.iterparse(str(input_path), events=("start", "end")):
        tag = elem.tag.rsplit("}", 1)[-1]

        if action == "start":
            depth += 1
            continue

        depth -= 1

        # Only <event> elements directly inside a <trace> (log > trace > event).
        if tag == "event" and depth == 2:
            event = {key: None for key in STREAMING_EVENT_KEYS}

            for child in elem:
                key = child.get("key")
                if key in event:
                    event[key] = child.get("value")

            trace_events.append(event)
            elem.clear()

        elif tag == "trace" and depth == 1:
            case_id = None

            for child in elem:
                if child.get("key") == "concept:name":
                    case_id = child.get("value")
                    break

            for event in trace_events:
                event["case:concept:name"] = case_id

            rows.extend(trace_events)
            trace_events = []
            elem.clear()

    df = pd.DataFrame(
        rows,
        columns=["case:concept:name", *STREAMING_EVENT_KEYS],
    )

    df["time:timestamp"] = pd.to_datetime(
        df["time:timestamp"],
        errors="coerce",
        utc=True,
        format="ISO8601",
    )

    if df["lifecycle:transition"].isna().all():
        df = df.drop(columns="lifecycle:transition")

    return df


def prepare_event_log(
    input_path: str,
    output_path: str,
    max_cases: int | None = 1000,
    random_state: int = 42,
    lifecycle: str | None = None,
    streaming: bool = False,
):
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input XES not found: {input_path}")

    print(f"Reading event log: {input_path}")

    if streaming:
        df = read_xes_streaming(input_path)
    else:
        df = pm4py.read_xes(str(input_path))

        if not isinstance(df, pd.DataFrame):
            df = pm4py.convert_to_dataframe(df)

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

    # Logs such as BPI 2017 record several lifecycle transitions per activity
    # (schedule, start, suspend, resume, complete, ...). Keeping only one
    # transition makes them comparable with the complete-only logs (BPI 2019).
    if lifecycle is not None:
        if "lifecycle:transition" not in df.columns:
            raise ValueError(
                "--lifecycle was given, but the log has no "
                "lifecycle:transition attribute"
            )

        print("\nLifecycle transitions:")
        print(df["lifecycle:transition"].value_counts())

        df = df[
            df["lifecycle:transition"].astype(str).str.lower()
            == lifecycle.lower()
        ].copy()

        print(f"\nKept only lifecycle:transition == {lifecycle}")

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

        if max_cases > len(valid_cases):
            print(
                f"\nWARNING: requested {max_cases} cases, but the log has "
                f"only {len(valid_cases)}. Using all cases."
            )

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
        description="Prepare a sampled baseline CSV from an XES event log."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to the original XES file",
    )

    parser.add_argument(
        "--output",
        required=True,
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

    parser.add_argument(
        "--lifecycle",
        default=None,
        help=(
            "Keep only events with this lifecycle:transition value, "
            "e.g. complete. Omit to keep all events."
        ),
    )

    parser.add_argument(
        "--streaming",
        action="store_true",
        help=(
            "Read only the needed attributes with a streaming XML parser. "
            "Use for very large logs that do not fit in memory with pm4py."
        ),
    )

    args = parser.parse_args()

    prepare_event_log(
        input_path=args.input,
        output_path=args.output,
        max_cases=None if args.max_cases == 0 else args.max_cases,
        random_state=args.random_state,
        lifecycle=args.lifecycle,
        streaming=args.streaming,
    )


if __name__ == "__main__":
    main()
