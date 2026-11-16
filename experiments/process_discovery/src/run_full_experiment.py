from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse

import pandas as pd

from config import (
    PREPARED_DIR,
    DEGRADED_DIR,
    DEGRADATION_DIMENSIONS,
    DEGRADATION_LEVELS,
    N_REPETITIONS,
    MINERS,
    METRICS_DIR,
)

from run_discovery_experiment import (
    append_results,
    get_output_paths,
    run_discovery_experiment,
)


def parse_str_list(values, default):
    if values is None:
        return default
    return values


def parse_int_list(values, default):
    if values is None:
        return default
    return [int(value) for value in values]


def clear_previous_results() -> None:
    """
    Deletes the previous discovery_results.csv if requested.

    Useful when running the full experiment from scratch.
    """
    results_path = Path(METRICS_DIR) / "discovery_results.csv"

    if results_path.exists():
        results_path.unlink()
        print(f"Deleted previous results: {results_path}")


def get_completed_runs(dataset_name: str) -> set[tuple[str, int, int]]:
    """
    Returns (dimension, level, repetition) of logs that already have results
    in the dataset's discovery_results.csv.
    """
    results_path = get_output_paths(dataset_name)["metrics"] / "discovery_results.csv"

    if not results_path.exists():
        return set()

    results = pd.read_csv(results_path)

    return {
        (row.dimension, int(row.degradation_level), int(row.repetition))
        for row in results.itertuples()
    }


def get_degraded_log_path(
    degraded_dir: str,
    dimension: str,
    level: int,
    repetition: int,
) -> Path:
    return Path(degraded_dir) / dimension / f"{dimension}_{level}_r{repetition}.csv"


def run_baseline(
    baseline_path: str,
    dataset_name: str,
    miners: list[str],
) -> None:
    """
    Runs all selected miners on the baseline prepared log.
    """
    print("\n==============================")
    print("Running baseline experiment")
    print("==============================")

    if not Path(baseline_path).exists():
        raise FileNotFoundError(f"Baseline file not found: {baseline_path}")

    run_discovery_experiment(
        input_path=baseline_path,
        dataset_name=dataset_name,
        dimension="baseline",
        degradation_level=0,
        repetition=0,
        miners=miners,
    )


def run_degraded_experiments(
    degraded_dir: str,
    dataset_name: str,
    dimensions: list[str],
    levels: list[int],
    repetitions: int,
    miners: list[str],
    skip_missing: bool = True,
    workers: int = 1,
    completed: set[tuple[str, int, int]] | None = None,
) -> None:
    """
    Runs the discovery experiment for all degraded logs.

    With workers > 1, the degraded logs are processed in parallel. Results are
    still appended in the same order as in a sequential run.

    Logs whose (dimension, level, repetition) is in completed are skipped.
    """
    completed = completed or set()
    tasks = []

    for dimension in dimensions:
        for level in levels:
            for repetition in range(1, repetitions + 1):
                if (dimension, level, repetition) in completed:
                    print(f"Already done, skipping: {dimension} {level}% r{repetition}")
                    continue

                input_path = get_degraded_log_path(
                    degraded_dir=degraded_dir,
                    dimension=dimension,
                    level=level,
                    repetition=repetition,
                )

                if not input_path.exists():
                    message = f"Missing degraded log: {input_path}"

                    if skip_missing:
                        print(f"Skipping. {message}")
                        continue

                    raise FileNotFoundError(message)

                tasks.append(
                    {
                        "input_path": str(input_path),
                        "dataset_name": dataset_name,
                        "dimension": dimension,
                        "degradation_level": level,
                        "repetition": repetition,
                        "miners": miners,
                    }
                )

    if workers <= 1:
        for task in tasks:
            print("\n==============================")
            print("Running degraded experiment")
            print(f"Dimension: {task['dimension']}")
            print(f"Level: {task['degradation_level']}%")
            print(f"Repetition: {task['repetition']}")
            print(f"Input: {task['input_path']}")
            print("==============================")

            run_discovery_experiment(**task)

        return

    output_csv = get_output_paths(dataset_name)["metrics"] / "discovery_results.csv"

    print(f"\nRunning {len(tasks)} degraded logs with {workers} workers...")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(run_discovery_experiment, **task, save_results=False)
            for task in tasks
        ]

        # Collect in submission order, so that the CSV has the same row order
        # as a sequential run.
        for task, future in zip(tasks, futures):
            results_df = future.result()
            append_results(results_df.to_dict("records"), str(output_csv))

            print(
                f"Saved: {task['dimension']} "
                f"{task['degradation_level']}% "
                f"r{task['repetition']}"
            )


def run_full_experiment(
    baseline_path: str,
    degraded_dir: str,
    dataset_name: str,
    dimensions: list[str],
    levels: list[int],
    repetitions: int,
    miners: list[str],
    include_baseline: bool = True,
    clear_results: bool = False,
    skip_missing: bool = True,
    workers: int = 1,
    resume: bool = False,
) -> None:
    """
    Runs the complete process discovery experiment.

    Matrix:
        baseline × miners
        +
        dimensions × levels × repetitions × miners

    With resume=True, logs that already have results in the dataset's
    discovery_results.csv are not run again.
    """
    if clear_results:
        clear_previous_results()

    completed = set()

    if resume:
        completed = get_completed_runs(dataset_name)
        print(f"Resuming: {len(completed)} logs already have results.")

        if ("baseline", 0, 0) in completed:
            include_baseline = False

    if include_baseline:
        run_baseline(
            baseline_path=baseline_path,
            dataset_name=dataset_name,
            miners=miners,
        )

    run_degraded_experiments(
        degraded_dir=degraded_dir,
        dataset_name=dataset_name,
        dimensions=dimensions,
        levels=levels,
        repetitions=repetitions,
        miners=miners,
        skip_missing=skip_missing,
        workers=workers,
        completed=completed,
    )

    print("\nFull experiment finished.")
    print(f"Results file: {get_output_paths(dataset_name)['metrics'] / 'discovery_results.csv'}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--baseline",
        default=f"{PREPARED_DIR}/bpi2019_baseline_1000_cases.csv",
        help="Path to prepared baseline CSV log.",
    )

    parser.add_argument(
        "--degraded-dir",
        default=DEGRADED_DIR,
        help="Directory containing degraded logs.",
    )

    parser.add_argument(
        "--dataset-name",
        default="bpi2019_1000",
        help="Dataset name stored in results.",
    )

    parser.add_argument(
        "--dimensions",
        nargs="+",
        default=None,
        help="Dimensions to run: accuracy completeness consistency timeliness.",
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
        "--miners",
        nargs="+",
        default=None,
        help="Miners to run: alpha heuristics inductive.",
    )

    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Skip baseline experiment.",
    )

    parser.add_argument(
        "--clear-results",
        action="store_true",
        help="Delete previous discovery_results.csv before running.",
    )

    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Raise error if a degraded log is missing.",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of degraded logs to process in parallel.",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip logs that already have results in discovery_results.csv.",
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

    miners = parse_str_list(
        args.miners,
        MINERS,
    )

    run_full_experiment(
        baseline_path=args.baseline,
        degraded_dir=args.degraded_dir,
        dataset_name=args.dataset_name,
        dimensions=dimensions,
        levels=levels,
        repetitions=args.repetitions,
        miners=miners,
        include_baseline=not args.skip_baseline,
        clear_results=args.clear_results,
        skip_missing=not args.fail_on_missing,
        workers=args.workers,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
