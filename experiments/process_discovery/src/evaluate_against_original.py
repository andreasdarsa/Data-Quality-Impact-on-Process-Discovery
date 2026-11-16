from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import argparse
from typing import Any, Dict

import pandas as pd
import pm4py

from run_discovery_experiment import (
    append_results,
    get_output_paths,
    load_process_log,
)
from evaluation import evaluate_model


OUTPUT_FILE = "discovery_results_vs_original.csv"

KEY_COLS = [
    "dataset",
    "dimension",
    "degradation_level",
    "repetition",
    "miner",
    "model_name",
]

# Inductive Miner models are by far the slowest to evaluate, so they are
# started first to keep all workers busy until the end.
MINER_PRIORITY = {
    "inductive": 0,
    "heuristics": 1,
    "alpha": 2,
}

_original_log = None


def init_worker(original_path: str) -> None:
    """
    Loads the original (non-degraded) log once per worker process.
    """
    global _original_log
    _original_log, _ = load_process_log(original_path)


def evaluate_saved_model(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates one saved Petri net against the original log.

    The model is not discovered again: it is read from its PNML file, so it is
    exactly the model that was evaluated against the degraded log.
    """
    row = {key: task[key] for key in KEY_COLS}
    row["evaluated_on"] = task["original_path"]

    try:
        net, initial_marking, final_marking = pm4py.read_pnml(task["pnml_path"])

        row.update(
            evaluate_model(
                log=_original_log,
                net=net,
                initial_marking=initial_marking,
                final_marking=final_marking,
            )
        )
        row["status"] = "ok"
        row["error"] = None

    except Exception as error:
        row["status"] = "failed"
        row["error"] = repr(error)

    return row


def evaluate_against_original(
    dataset_name: str,
    original_path: str,
    workers: int = 1,
) -> None:
    """
    Evaluates every model of a finished experiment against the original log.

    Writes discovery_results_vs_original.csv next to discovery_results.csv.
    Models that already have a result in that file are skipped, so an
    interrupted run can simply be started again.
    """
    paths = get_output_paths(dataset_name)

    discovery = pd.read_csv(paths["metrics"] / "discovery_results.csv")
    discovery = discovery[discovery["status"] == "ok"]

    output_csv = paths["metrics"] / OUTPUT_FILE

    done = set()
    if output_csv.exists():
        done = set(pd.read_csv(output_csv)["model_name"])

    tasks = [
        {
            **{key: row[key] for key in KEY_COLS},
            "pnml_path": str(paths["pnml"] / f"{row['model_name']}.pnml"),
            "original_path": original_path,
        }
        for row in discovery.to_dict("records")
        if row["model_name"] not in done
    ]

    tasks.sort(key=lambda task: MINER_PRIORITY.get(task["miner"], len(MINER_PRIORITY)))

    print(f"Dataset: {dataset_name}")
    print(f"Original log: {original_path}")
    print(f"Already evaluated: {len(done)}, to evaluate: {len(tasks)}")

    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=init_worker,
        initargs=(original_path,),
    ) as executor:
        futures = [executor.submit(evaluate_saved_model, task) for task in tasks]

        for number, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            append_results([row], str(output_csv))

            print(
                f"[{number}/{len(tasks)}] {row['model_name']}: {row['status']}",
                flush=True,
            )

    # Same row order as discovery_results.csv.
    results = pd.read_csv(output_csv)
    order = {name: index for index, name in enumerate(discovery["model_name"])}
    results = results.sort_values("model_name", key=lambda names: names.map(order))
    results.to_csv(output_csv, index=False)

    print(f"\nSaved: {output_csv}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the models discovered from degraded logs against the "
            "original (non-degraded) log."
        )
    )

    parser.add_argument(
        "--dataset-name",
        required=True,
        help="Dataset name used in run_full_experiment.py, e.g. bpi2017_2000.",
    )

    parser.add_argument(
        "--original",
        required=True,
        help="Path to the prepared baseline CSV that the degraded logs came from.",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of models to evaluate in parallel.",
    )

    args = parser.parse_args()

    evaluate_against_original(
        dataset_name=args.dataset_name,
        original_path=args.original,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
