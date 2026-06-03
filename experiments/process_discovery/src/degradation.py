from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from config import (
    CASE_ID_COL,
    ACTIVITY_COL,
    COMPLETE_TIMESTAMP_COL,
)


SUPPORTED_DEGRADATIONS = [
    "accuracy",
    "completeness",
    "consistency",
    "timeliness",
]


def validate_level(level: int) -> None:
    """
    Validates degradation level.

    The level represents the percentage of events affected.
    Example:
        level = 10 means approximately 10% of events are degraded.
    """
    if not isinstance(level, int):
        raise TypeError("Degradation level must be an integer.")

    if level < 0 or level > 100:
        raise ValueError("Degradation level must be between 0 and 100.")


def get_random_generator(random_state: int | None = None) -> np.random.Generator:
    return np.random.default_rng(random_state)


def sample_event_indices(
    df: pd.DataFrame,
    level: int,
    random_state: int | None = None,
) -> np.ndarray:
    """
    Samples event row indices according to the degradation level.
    """
    validate_level(level)

    if level == 0 or len(df) == 0:
        return np.array([], dtype=int)

    n_events = len(df)
    n_affected = max(1, int(round(n_events * level / 100)))

    rng = get_random_generator(random_state)

    return rng.choice(
        df.index.to_numpy(),
        size=min(n_affected, n_events),
        replace=False,
    )


def recompute_event_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recomputes event_index inside each case after degradation.

    We keep event_index only as a deterministic tie-breaker for events
    with identical complete_timestamp values.
    """
    df = df.copy()

    if COMPLETE_TIMESTAMP_COL in df.columns:
        df[COMPLETE_TIMESTAMP_COL] = pd.to_datetime(
            df[COMPLETE_TIMESTAMP_COL],
            errors="coerce",
        )

    sort_cols = [CASE_ID_COL, COMPLETE_TIMESTAMP_COL]

    if "event_index" in df.columns:
        sort_cols.append("event_index")

    df = df.sort_values(sort_cols).reset_index(drop=True)
    df["event_index"] = df.groupby(CASE_ID_COL).cumcount()

    return df


def degrade_accuracy(
    df: pd.DataFrame,
    level: int,
    random_state: int | None = None,
) -> pd.DataFrame:
    """
    Applies accuracy degradation.

    Accuracy degradation simulates wrong recorded values.

    For process discovery, the most relevant accuracy errors are:
    - wrong activity labels
    - wrong case assignment

    We avoid timestamp changes here because timestamp-related errors belong
    to timeliness degradation.
    """
    degraded = df.copy()
    rng = get_random_generator(random_state)

    selected_indices = sample_event_indices(
        degraded,
        level,
        random_state,
    )

    if len(selected_indices) == 0:
        return recompute_event_index(degraded)

    activities = degraded[ACTIVITY_COL].dropna().unique()
    case_ids = degraded[CASE_ID_COL].dropna().unique()

    if len(activities) <= 1 and len(case_ids) <= 1:
        return recompute_event_index(degraded)

    # 70% wrong activity labels, 30% wrong case assignment.
    rng.shuffle(selected_indices)

    split_point = int(round(len(selected_indices) * 0.7))

    activity_error_indices = selected_indices[:split_point]
    case_error_indices = selected_indices[split_point:]

    if len(activities) > 1:
        for idx in activity_error_indices:
            current_activity = degraded.at[idx, ACTIVITY_COL]

            possible_activities = [
                activity
                for activity in activities
                if activity != current_activity
            ]

            if possible_activities:
                degraded.at[idx, ACTIVITY_COL] = rng.choice(possible_activities)

    if len(case_ids) > 1:
        for idx in case_error_indices:
            current_case = degraded.at[idx, CASE_ID_COL]

            possible_cases = [
                case_id
                for case_id in case_ids
                if case_id != current_case
            ]

            if possible_cases:
                degraded.at[idx, CASE_ID_COL] = rng.choice(possible_cases)

    return recompute_event_index(degraded)


def degrade_completeness(
    df: pd.DataFrame,
    level: int,
    random_state: int | None = None,
) -> pd.DataFrame:
    """
    Applies completeness degradation.

    Completeness degradation simulates missing events.

    We remove events from the log instead of setting values to NaN because
    missing case/activity/timestamp values would later be dropped before
    discovery anyway.
    """
    degraded = df.copy()

    selected_indices = sample_event_indices(
        degraded,
        level,
        random_state,
    )

    if len(selected_indices) == 0:
        return recompute_event_index(degraded)

    # Avoid removing the only event of a case when possible.
    case_sizes = degraded.groupby(CASE_ID_COL)[CASE_ID_COL].transform("size")
    removable_indices = degraded[case_sizes > 1].index.to_numpy()

    selected_indices = np.intersect1d(selected_indices, removable_indices)

    if len(selected_indices) == 0:
        return recompute_event_index(degraded)

    degraded = degraded.drop(index=selected_indices)

    return recompute_event_index(degraded)


def make_activity_variant(
    activity: str,
    rng: np.random.Generator,
) -> str:
    """
    Creates inconsistent labels for the same activity.

    Example:
        'Record Goods Receipt'
        -> 'record goods receipt'
        -> 'Record_Goods_Receipt'
        -> 'Record Goods Receipt__variant'
    """
    activity = str(activity)

    variant_type = rng.choice(
        [
            "lowercase",
            "underscore",
            "suffix",
            "compact",
        ]
    )

    if variant_type == "lowercase":
        return activity.lower()

    if variant_type == "underscore":
        return activity.replace(" ", "_")

    if variant_type == "suffix":
        return f"{activity}__variant"

    if variant_type == "compact":
        return activity.replace(" ", "")

    return activity


def degrade_consistency(
    df: pd.DataFrame,
    level: int,
    random_state: int | None = None,
) -> pd.DataFrame:
    """
    Applies consistency degradation.

    Consistency degradation simulates representation inconsistencies:
    - same activity appears with different names
    - duplicate events are inserted

    This is expected to increase the apparent number of activities and
    potentially make discovered models more complex.
    """
    degraded = df.copy()
    rng = get_random_generator(random_state)

    selected_indices = sample_event_indices(
        degraded,
        level,
        random_state,
    )

    if len(selected_indices) == 0:
        return recompute_event_index(degraded)

    rng.shuffle(selected_indices)

    # 70% inconsistent labels, 30% duplicated events.
    split_point = int(round(len(selected_indices) * 0.7))

    rename_indices = selected_indices[:split_point]
    duplicate_indices = selected_indices[split_point:]

    for idx in rename_indices:
        current_activity = degraded.at[idx, ACTIVITY_COL]
        degraded.at[idx, ACTIVITY_COL] = make_activity_variant(
            current_activity,
            rng,
        )

    duplicates = degraded.loc[duplicate_indices].copy()

    if not duplicates.empty:
        # Slightly change event_index so duplicated events remain distinguishable
        # as separate rows before recomputing event_index.
        if "event_index" in duplicates.columns:
            duplicates["event_index"] = duplicates["event_index"] + 0.1

        degraded = pd.concat(
            [degraded, duplicates],
            ignore_index=True,
        )

    return recompute_event_index(degraded)


def shift_timestamp(
    timestamp: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.Timestamp:
    """
    Shifts a completion timestamp forwards or backwards.

    We use only complete_timestamp because BPI 2019 does not provide
    real start timestamps.
    """
    if pd.isna(timestamp):
        return timestamp

    direction = rng.choice([-1, 1])

    # Random shift between 1 hour and 14 days.
    hours = int(rng.integers(1, 24 * 14 + 1))

    return timestamp + pd.Timedelta(hours=direction * hours)


def swap_timestamps_within_cases(
    df: pd.DataFrame,
    selected_indices: np.ndarray,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Swaps complete_timestamp values between selected events inside the same case.

    This simulates out-of-order or delayed event recording.
    """
    degraded = df.copy()

    selected_df = degraded.loc[selected_indices]

    for _, case_group in selected_df.groupby(CASE_ID_COL):
        indices = case_group.index.to_numpy()

        if len(indices) < 2:
            continue

        shuffled_indices = indices.copy()
        rng.shuffle(shuffled_indices)

        original_timestamps = degraded.loc[indices, COMPLETE_TIMESTAMP_COL].copy()
        degraded.loc[indices, COMPLETE_TIMESTAMP_COL] = degraded.loc[
            shuffled_indices,
            COMPLETE_TIMESTAMP_COL,
        ].to_numpy()

        # If shuffling accidentally keeps the same order, force a simple reversal.
        if degraded.loc[indices, COMPLETE_TIMESTAMP_COL].equals(original_timestamps):
            degraded.loc[indices, COMPLETE_TIMESTAMP_COL] = original_timestamps.iloc[::-1].to_numpy()

    return degraded


def degrade_timeliness(
    df: pd.DataFrame,
    level: int,
    random_state: int | None = None,
) -> pd.DataFrame:
    """
    Applies timeliness degradation.

    Timeliness degradation affects only complete_timestamp.

    It simulates:
    - delayed or early event recording
    - out-of-order events inside cases

    Important:
        We do NOT create or alter start_timestamp because BPI 2019 does not
        provide real event start timestamps.
    """
    degraded = df.copy()
    rng = get_random_generator(random_state)

    degraded[COMPLETE_TIMESTAMP_COL] = pd.to_datetime(
        degraded[COMPLETE_TIMESTAMP_COL],
        errors="coerce",
    )

    selected_indices = sample_event_indices(
        degraded,
        level,
        random_state,
    )

    if len(selected_indices) == 0:
        return recompute_event_index(degraded)

    rng.shuffle(selected_indices)

    # 50% timestamp shifts, 50% swaps inside cases.
    split_point = int(round(len(selected_indices) * 0.5))

    shift_indices = selected_indices[:split_point]
    swap_indices = selected_indices[split_point:]

    for idx in shift_indices:
        degraded.at[idx, COMPLETE_TIMESTAMP_COL] = shift_timestamp(
            degraded.at[idx, COMPLETE_TIMESTAMP_COL],
            rng,
        )

    degraded = swap_timestamps_within_cases(
        degraded,
        swap_indices,
        rng,
    )

    return recompute_event_index(degraded)


def degrade_log(
    df: pd.DataFrame,
    dimension: str,
    level: int,
    random_state: int | None = None,
) -> pd.DataFrame:
    """
    Dispatch function for all supported degradation dimensions.
    """
    dimension = dimension.lower().strip()

    degradation_functions: dict[str, Callable[[pd.DataFrame, int, int | None], pd.DataFrame]] = {
        "accuracy": degrade_accuracy,
        "completeness": degrade_completeness,
        "consistency": degrade_consistency,
        "timeliness": degrade_timeliness,
    }

    if dimension not in degradation_functions:
        raise ValueError(
            f"Unsupported degradation dimension: {dimension}. "
            f"Supported dimensions are: {SUPPORTED_DEGRADATIONS}"
        )

    return degradation_functions[dimension](
        df,
        level,
        random_state,
    )


def get_degradation_summary(
    original_df: pd.DataFrame,
    degraded_df: pd.DataFrame,
) -> dict:
    """
    Returns basic statistics before and after degradation.
    Useful for logging and result interpretation.
    """
    return {
        "events_before_degradation": len(original_df),
        "events_after_degradation": len(degraded_df),
        "cases_before_degradation": original_df[CASE_ID_COL].nunique(),
        "cases_after_degradation": degraded_df[CASE_ID_COL].nunique(),
        "activities_before_degradation": original_df[ACTIVITY_COL].nunique(),
        "activities_after_degradation": degraded_df[ACTIVITY_COL].nunique(),
    }
