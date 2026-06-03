from pathlib import Path
import argparse
from typing import Any, Dict

import pandas as pd
import pm4py

from config import (
    CASE_ID_COL,
    ACTIVITY_COL,
    COMPLETE_TIMESTAMP_COL,
    MINERS,
    RESULTS_DIR,
    METRICS_DIR,
    PNML_DIR,
    FIGURES_DIR,
)

from discovery import discover_model
from evaluation import evaluate_model


def ensure_directories() -> None:
    """
    Creates all output directories if they do not already exist.
    """
    Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(METRICS_DIR).mkdir(parents=True, exist_ok=True)
    Path(PNML_DIR).mkdir(parents=True, exist_ok=True)
    Path(FIGURES_DIR).mkdir(parents=True, exist_ok=True)
    Path(FIGURES_DIR, "model_visualizations").mkdir(parents=True, exist_ok=True)


def load_process_log(csv_path: str):
    """
    Loads a CSV event log and converts it to a PM4Py EventLog.

    Important:
    For BPI Challenge 2019 we only use complete_timestamp.
    We do NOT create or use artificial start timestamps.
    """
    df = pd.read_csv(csv_path)

    required_cols = [
        CASE_ID_COL,
        ACTIVITY_COL,
        COMPLETE_TIMESTAMP_COL,
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    initial_events = len(df)
    initial_cases = df[CASE_ID_COL].nunique()
    initial_activities = df[ACTIVITY_COL].nunique()

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

    # Αν υπάρχει event_index από prepare_bpi2019.py, το χρησιμοποιούμε ως tie-breaker.
    # Αν δεν υπάρχει, δημιουργούμε ένα απλό index με βάση την τρέχουσα σειρά.
    if "event_index" not in df.columns:
        df["event_index"] = df.groupby(CASE_ID_COL).cumcount()

    df = df.sort_values(
        by=[
            CASE_ID_COL,
            COMPLETE_TIMESTAMP_COL,
            "event_index",
        ]
    ).reset_index(drop=True)

    used_events = len(df)
    used_cases = df[CASE_ID_COL].nunique()
    used_activities = df[ACTIVITY_COL].nunique()

    formatted_df = pm4py.format_dataframe(
        df,
        case_id=CASE_ID_COL,
        activity_key=ACTIVITY_COL,
        timestamp_key=COMPLETE_TIMESTAMP_COL,
    )

    log = pm4py.convert_to_event_log(formatted_df)

    log_info = {
        "events_before": initial_events,
        "events_after": used_events,
        "dropped_events": initial_events - used_events,
        "cases_before": initial_cases,
        "cases_after": used_cases,
        "activities_before": initial_activities,
        "activities_after": used_activities,
    }

    return log, log_info


def save_model_outputs(
    net,
    initial_marking,
    final_marking,
    model_name: str,
) -> Dict[str, Any]:
    """
    Saves PNML and PNG visualization for a discovered Petri net.

    If visualization fails, the experiment continues.
    """
    output_info = {
        "pnml_path": None,
        "visualization_path": None,
        "pnml_saved": False,
        "visualization_saved": False,
        "visualization_error": None,
        "pnml_error": None,
    }

    pnml_path = Path(PNML_DIR) / f"{model_name}.pnml"
    visualization_path = Path(FIGURES_DIR) / "model_visualizations" / f"{model_name}.png"

    try:
        pm4py.write_pnml(
            net,
            initial_marking,
            final_marking,
            str(pnml_path),
        )

        output_info["pnml_path"] = str(pnml_path)
        output_info["pnml_saved"] = True

    except Exception as error:
        output_info["pnml_error"] = repr(error)

    try:
        pm4py.save_vis_petri_net(
            net,
            initial_marking,
            final_marking,
            str(visualization_path),
        )

        output_info["visualization_path"] = str(visualization_path)
        output_info["visualization_saved"] = True

    except Exception as error:
        output_info["visualization_error"] = repr(error)

    return output_info


def append_results(results: list[Dict[str, Any]], output_path: str) -> None:
    """
    Appends experiment results to discovery_results.csv.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    new_results = pd.DataFrame(results)

    if output_path.exists():
        old_results = pd.read_csv(output_path)
        all_results = pd.concat([old_results, new_results], ignore_index=True)
    else:
        all_results = new_results

    all_results.to_csv(output_path, index=False)


def run_discovery_experiment(
    input_path: str,
    dataset_name: str,
    dimension: str,
    degradation_level: int,
    repetition: int,
    miners: list[str] | None = None,
) -> pd.DataFrame:
    """
    Runs Alpha Miner, Heuristics Miner and Inductive Miner on one event log.
    """
    ensure_directories()

    miners = miners or MINERS

    log, log_info = load_process_log(input_path)

    results = []

    for miner_name in miners:
        print(f"\nRunning {miner_name} miner...")

        model_name = (
            f"{dataset_name}_"
            f"{dimension}_"
            f"{degradation_level}_"
            f"r{repetition}_"
            f"{miner_name}"
        )

        row = {
            "dataset": dataset_name,
            "dimension": dimension,
            "degradation_level": degradation_level,
            "repetition": repetition,
            "miner": miner_name,
            "input_file": input_path,
            "model_name": model_name,
            **log_info,
        }

        try:
            net, initial_marking, final_marking = discover_model(
                log=log,
                miner_name=miner_name,
            )

            metrics = evaluate_model(
                log=log,
                net=net,
                initial_marking=initial_marking,
                final_marking=final_marking,
            )

            output_info = save_model_outputs(
                net=net,
                initial_marking=initial_marking,
                final_marking=final_marking,
                model_name=model_name,
            )

            row.update(metrics)
            row.update(output_info)
            row["status"] = "ok"
            row["error"] = None

        except Exception as error:
            row["status"] = "failed"
            row["error"] = repr(error)

        results.append(row)

    output_csv = Path(METRICS_DIR) / "discovery_results.csv"
    append_results(results, str(output_csv))

    results_df = pd.DataFrame(results)

    print("\nExperiment finished.")
    print(f"Results saved to: {output_csv}")
    print(results_df)

    return results_df


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
        help="Path to prepared or degraded CSV event log.",
    )

    parser.add_argument(
        "--dataset-name",
        default="bpi2019",
        help="Dataset name used in the results file.",
    )

    parser.add_argument(
        "--dimension",
        default="baseline",
        help="baseline, accuracy, completeness, consistency, or timeliness.",
    )

    parser.add_argument(
        "--level",
        type=int,
        default=0,
        help="Degradation level. Use 0 for baseline.",
    )

    parser.add_argument(
        "--repetition",
        type=int,
        default=0,
        help="Repetition id. Use 0 for baseline.",
    )

    parser.add_argument(
        "--miners",
        nargs="+",
        default=None,
        help="Optional list of miners: alpha heuristics inductive.",
    )

    args = parser.parse_args()

    run_discovery_experiment(
        input_path=args.input,
        dataset_name=args.dataset_name,
        dimension=args.dimension,
        degradation_level=args.level,
        repetition=args.repetition,
        miners=args.miners,
    )


if __name__ == "__main__":
    main()
