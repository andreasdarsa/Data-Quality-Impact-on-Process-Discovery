RAW_LOG_PATH = "data/raw/BPI_Challenge_2019.xes"

PREPARED_DIR = "data/prepared"
DEGRADED_DIR = "data/degraded"

RESULTS_DIR = "experiments/process_discovery/results"
METRICS_DIR = "experiments/process_discovery/results/metrics"
PNML_DIR = "experiments/process_discovery/results/models/pnml"
FIGURES_DIR = "experiments/process_discovery/results/figures"

CASE_ID_COL = "case_id"
ACTIVITY_COL = "activity"
COMPLETE_TIMESTAMP_COL = "complete_timestamp"

# BPI Challenge 2019 provides only completion timestamps.
# We do not create or use artificial start timestamps.

MINERS = ["alpha", "heuristics", "inductive"]

DEGRADATION_DIMENSIONS = [
    "accuracy",
    "completeness",
    "consistency",
    "timeliness",
]

DEGRADATION_LEVELS = [10, 20, 30]

N_REPETITIONS = 5
RANDOM_STATE = 42
