from pathlib import Path
import argparse
from typing import Any

import pandas as pd

from config import (
    PREPARED_DIR,
    DEGRADED_DIR,
    DEGRADATION_DIMENSIONS,
    DEGRADATION_LEVELS,
    N_REPETITIONS,
    RANDOM_STATE,
    CASE_ID_COL,
    ACTIVITY_COL,
    COMPLETE_TIMESTAMP_COL,
)

from degradation import (
    degrade_log,
    get_degradation_summary,
)


def validate_input_log(df: pd.DataFrame) -> None:
    """
    Validates that the baseline log has the minimum required columns.

    For BPI Challenge 2019, we use only complete_timestamp.
    We do not require or create start_timestamp.
    """
    required_cols = [
        CASE_ID_COL,
        ACTIVITY_COL,
        COMPLETE_TIMESTAMP_COL,
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")


def load_baseline_log(input_path: str) -> pd.DataFrame:
    """
    Loads the prepared baseline CSV.
    """
    df = pd.read_csv(input_path)

    validate_input_log(df)

    df[COMPLETE_TIMESTAMP_COL] = pd.to_datetime(
        df[COMPLETE_TIMESTAMP_COL],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            CASE_ID_COL,
            ACTIVITY_COL,
            COMPLETE_TIMESTAMP_COL,
        ]
    ).copy()

    if "event_index" not in df.columns:
        df["event_index"] = df.groupby(CASE_ID_COL).cumcount()

    df = df.sort_values(
        by=[
            CASE_ID_COL,
            COMPLETE_TIMESTAMP_COL,
            "event_index",
        ]
    ).reset_index(drop=True)

    return df


def make_output_path(
    output_dir: str,
    dimension: str,
    level: int,
    repetition: int,
) -> Path:
    """
    Creates the output path for one degraded log.
    """
    dimension_dir = Path(output_dir) / dimension
    dimension_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{dimension}_{level}_r{repetition}.csv"

    return dimension_dir / filename


def make_seed(
    base_seed: int,
    dimension: str,
    level: int,
    repetition: int,
) -> int:
    """
    Creates a deterministic but different random seed for each generated log.

    This ensures:
    - reproducibility
    - different degraded samples across repetitions
    """
    dimension_offset = sum(ord(char) for char in dimension)

    return base_seed + dimension_offset + level * 100 + repetition


def generate_single_degraded_log(
    baseline_df: pd.DataFrame,
    output_dir: str,
    dimension: str,
    level: int,
    repetition: int,
    base_random_state: int,
) -> dict[str, Any]:
    """
    Generates one degraded CSV log and returns metadata about it.
    """
    random_state = make_seed(
        base_seed=base_random_state,
        dimension=dimension,
        level=level,
        repetition=repetition,
    )

    degraded_df = degrade_log(
        df=baseline_df,
        dimension=dimension,
        level=level,
        random_state=random_state,
    )

    output_path = make_output_path(
        output_dir=output_dir,
        dimension=dimension,
        level=level,
        repetition=repetition,
    )

    degraded_df.to_csv(output_path, index=False)

    summary = get_degradation_summary(
        original_df=baseline_df,
        degraded_df=degraded_df,
    )

    metadata = {
        "dimension": dimension,
        "degradation_level": level,
        "repetition": repetition,
        "random_state": random_state,
        "output_file": str(output_path),
        **summary,
    }

    return metadata


def generate_all_degraded_logs(
    input_path: str,
    output_dir: str,
    dimensions: list[str],
    levels: list[int],
    repetitions: int,
    random_state: int,
) -> pd.DataFrame:
    """
    Generates all degraded logs for the experiment matrix.
    """
    baseline_df = load_baseline_log(input_path)

    print("Loaded baseline log.")
    print(f"Input: {input_path}")
    print(f"Events: {len(baseline_df)}")
    print(f"Cases: {baseline_df[CASE_ID_COL].nunique()}")
    print(f"Activities: {baseline_df[ACTIVITY_COL].nunique()}")

    all_metadata = []

    for dimension in dimensions:
        for level in levels:
            for repetition in range(1, repetitions + 1):
                print(
                    f"\nGenerating degraded log: "
                    f"dimension={dimension}, "
                    f"level={level}, "
                    f"repetition={repetition}"
                )

                metadata = generate_single_degraded_log(
                    baseline_df=baseline_df,
                    output_dir=output_dir,
                    dimension=dimension,
                    level=level,
                    repetition=repetition,
                    base_random_state=random_state,
                )

                all_metadata.append(metadata)

                print(f"Saved: {metadata['output_file']}")
                print(
                    f"Events: "
                    f"{metadata['events_before_degradation']} -> "
                    f"{metadata['events_after_degradation']}"
                )
                print(
                    f"Activities: "
                    f"{metadata['activities_before_degradation']} -> "
                    f"{metadata['activities_after_degradation']}"
                )

    manifest_df = pd.DataFrame(all_metadata)

    manifest_path = Path(output_dir) / "degradation_manifest.csv"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_df.to_csv(manifest_path, index=False)

    print("\nAll degraded logs generated.")
    print(f"Manifest saved to: {manifest_path}")

    return manifest_df


def parse_int_list(values: list[str] | None, default: list[int]) -> list[int]:
    """
    Parses command-line integer lists.
    """
    if values is None:
        return default

    return [int(value) for value in values]


def parse_str_list(values: list[str] | None, default: list[str]) -> list[str]:
    """
    Parses command-line string lists.
    """
    if values is None:
        return default

    return values


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default=f"{PREPARED_DIR}/bpi2019_baseline_1000_cases.csv",
        help="Path to prepared baseline CSV log.",
    )

    parser.add_argument(
        "--output-dir",
        default=DEGRADED_DIR,
        help="Directory where degraded logs will be saved.",
    )

    parser.add_argument(
        "--dimensions",
        nargs="+",
        default=None,
        help="Degradation dimensions to generate.",
    )

    parser.add_argument(
        "--levels",
        nargs="+",
        default=None,
        help="Degradation levels, e.g. 10 20 30.",
    )

    parser.add_argument(
        "--repetitions",
        type=int,
        default=N_REPETITIONS,
        help="Number of repetitions per dimension and level.",
    )

    parser.add_argument(
        "--random-state",
        type=int,
        default=RANDOM_STATE,
        help="Base random seed.",
    )

    args = parser.parse_args()

    dimensions = parse_str_list(
        args.dimensions,
        DEGRADATION_DIMENSIONS,
    )

    levels = parse_int_list(
        args.levels,
        DEGRADATION_LEVELS,
    )

    generate_all_degraded_logs(
        input_path=args.input,
        output_dir=args.output_dir,
        dimensions=dimensions,
        levels=levels,
        repetitions=args.repetitions,
        random_state=args.random_state,
    )


if __name__ == "__main__":
    main()
