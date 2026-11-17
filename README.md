# Process Discovery Experiment - BPI Challenge 2019

This module implements the second experimental part of the thesis:

> How does data quality affect process discovery?

The experiment uses the **BPI Challenge 2019** event log and evaluates how controlled data quality degradation affects discovered process models.

The main focus is on the following data quality dimensions:

- Accuracy
- Completeness
- Consistency
- Timeliness

The discovered models are evaluated using:

- Fitness
- Precision
- Generalization
- Simplicity
- Structural Petri net metrics:
  - Places
  - Transitions
  - Visible transitions
  - Hidden transitions
  - Arcs

---

## Important note about timestamps

The BPI Challenge 2019 event log contains only a completion timestamp:

```text
time:timestamp
```

In this project, it is mapped to:

```text
complete_timestamp
```

No artificial `start_timestamp` is created or used.

This is especially important for the timeliness degradation scenarios. Timeliness-related degradation is applied only to `complete_timestamp`.

---

## Repository structure

```text
experiments/process_discovery/
│
├── src/
│   ├── config.py
│   ├── prepare_bpi2019.py
│   ├── discovery.py
│   ├── evaluation.py
│   ├── degradation.py
│   ├── generate_degraded_logs.py
│   ├── run_discovery_experiment.py
│   ├── run_full_experiment.py
│   └── plots.py
│
├── results/
│   ├── metrics/
│   │   ├── discovery_results.csv
│   │   └── aggregated_results.csv
│   │
│   ├── models/
│   │   └── pnml/
│   │
│   └── figures/
│       └── model_visualizations/
│
└── README.md
```

The `src/` directory contains the experiment code.

The `results/` directory is used for generated outputs. Some result files or subfolders may be ignored by Git, depending on the `.gitignore` configuration.

---

## Local data and generated artifacts

The following paths are expected to exist locally when running the experiment, but they are not necessarily tracked by Git:

```text
data/
│
├── raw/
│   └── BPI_Challenge_2019.xes
│
├── prepared/
│   └── bpi2019_baseline_1000_cases.csv
│
└── degraded/
    ├── accuracy/
    ├── completeness/
    ├── consistency/
    └── timeliness/
```

The following outputs are also generated locally:

```text
experiments/process_discovery/results/models/pnml/
experiments/process_discovery/results/figures/model_visualizations/
```

These files and folders are typically excluded from version control because they can be large and can be regenerated from the experiment scripts.

If the repository is cloned on a new machine, the raw BPI 2019 `.xes` file must be placed manually in:

```text
data/raw/BPI_Challenge_2019.xes
```

Then the prepared and degraded datasets can be regenerated using the commands below.

---

## Environment setup

From the root folder of the project:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install pm4py pandas numpy matplotlib tqdm openpyxl graphviz
```

Optional:

```powershell
pip freeze > requirements.txt
```

---

## Configuration

The main experiment parameters are defined in:

```text
experiments/process_discovery/src/config.py
```

Current default setup:

```python
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
```

---

## Experimental pipeline

The complete pipeline is:

```text
Raw BPI 2019 XES log
        ↓
Prepared baseline CSV subset
        ↓
Controlled degradation scenarios
        ↓
Process discovery
        ↓
Model evaluation
        ↓
Results and plots
```

---

## Step 1 - Prepare BPI 2019 baseline subset

The raw log must be available locally as:

```text
data/raw/BPI_Challenge_2019.xes
```

To create a baseline subset of 1000 cases:

```powershell
python experiments/process_discovery/src/prepare_bpi2019.py `
  --input data/raw/BPI_Challenge_2019.xes `
  --output data/prepared/bpi2019_baseline_1000_cases.csv `
  --max-cases 1000
```

Expected local output:

```text
data/prepared/bpi2019_baseline_1000_cases.csv
```

Minimum expected columns:

```text
case_id
activity
complete_timestamp
event_index
```

---

## Step 2 - Run discovery on baseline log

To test the pipeline with only the Inductive Miner:

```powershell
python experiments/process_discovery/src/run_discovery_experiment.py `
  --input data/prepared/bpi2019_baseline_1000_cases.csv `
  --dataset-name bpi2019_1000 `
  --dimension baseline `
  --level 0 `
  --repetition 0 `
  --miners inductive
```

To run all miners on the baseline log:

```powershell
python experiments/process_discovery/src/run_discovery_experiment.py `
  --input data/prepared/bpi2019_baseline_1000_cases.csv `
  --dataset-name bpi2019_1000 `
  --dimension baseline `
  --level 0 `
  --repetition 0
```

This runs:

```text
Alpha Miner
Heuristics Miner
Inductive Miner
```

---

## Step 3 - Generate degraded logs

To generate all degraded logs for all dimensions, levels and repetitions:

```powershell
python experiments/process_discovery/src/generate_degraded_logs.py `
  --input data/prepared/bpi2019_baseline_1000_cases.csv `
  --output-dir data/degraded `
  --levels 10 20 30 `
  --repetitions 5
```

This creates local degraded logs for:

```text
accuracy      10%, 20%, 30%
completeness  10%, 20%, 30%
consistency   10%, 20%, 30%
timeliness    10%, 20%, 30%
```

Each scenario is repeated multiple times.

Example generated files:

```text
data/degraded/accuracy/accuracy_10_r1.csv
data/degraded/completeness/completeness_20_r3.csv
data/degraded/consistency/consistency_30_r5.csv
data/degraded/timeliness/timeliness_10_r1.csv
```

A manifest is also generated locally:

```text
data/degraded/degradation_manifest.csv
```

---

## Degradation scenarios

### Accuracy

Simulates wrongly recorded values.

Examples:

```text
wrong activity labels
wrong case assignment
```

Timestamp errors are not included here, because timestamp-related errors are handled under timeliness.

### Completeness

Simulates missing events.

Events are removed from the log.

### Consistency

Simulates inconsistent representations of the same information.

Examples:

```text
Record Goods Receipt
record goods receipt
Record_Goods_Receipt
Record Goods Receipt__variant
```

Duplicate events may also be inserted.

### Timeliness

Simulates problems related to the recording time of events.

Only `complete_timestamp` is altered.

Examples:

```text
timestamp shifts
timestamp swaps within the same case
```

No `start_timestamp` is created or modified.

---

## Step 4 - Run full experiment

To run the full experiment with all miners:

```powershell
python experiments/process_discovery/src/run_full_experiment.py `
  --baseline data/prepared/bpi2019_baseline_1000_cases.csv `
  --degraded-dir data/degraded `
  --dataset-name bpi2019_1000 `
  --clear-results
```

This produces:

```text
experiments/process_discovery/results/metrics/discovery_results.csv
```

The full matrix is:

```text
Baseline:
1 baseline log × 3 miners = 3 evaluations

Degraded:
4 dimensions × 3 levels × 5 repetitions × 3 miners = 180 evaluations

Total:
183 evaluations
```

For a smaller test run using only the Inductive Miner:

```powershell
python experiments/process_discovery/src/run_full_experiment.py `
  --baseline data/prepared/bpi2019_baseline_1000_cases.csv `
  --degraded-dir data/degraded `
  --dataset-name bpi2019_1000 `
  --miners inductive `
  --levels 10 `
  --repetitions 1 `
  --clear-results
```

---

## Step 5 - Generate plots

After the experiment finishes:

```powershell
python experiments/process_discovery/src/plots.py `
  --input experiments/process_discovery/results/metrics/discovery_results.csv `
  --output-dir experiments/process_discovery/results/figures
```

Expected generated plots include:

```text
fitness_by_accuracy.png
precision_by_accuracy.png
generalization_by_accuracy.png
simplicity_by_accuracy.png
arcs_by_timeliness.png
transitions_by_consistency.png
```

An aggregated results file is also produced:

```text
experiments/process_discovery/results/metrics/aggregated_results.csv
```

---

## Main results file

The main output file is:

```text
experiments/process_discovery/results/metrics/discovery_results.csv
```

It contains one row per:

```text
dataset × dimension × degradation level × repetition × miner
```

Important columns include:

```text
dataset
dimension
degradation_level
repetition
miner
fitness
precision
generalization
simplicity
places
transitions
visible_transitions
hidden_transitions
arcs
events_before
events_after
cases_before
cases_after
activities_before
activities_after
status
error
```

---

## Git-ignored files and folders

The following paths are intentionally ignored by Git in this project:

```text
/experiments/process_discovery/results/models/pnml/
/experiments/process_discovery/results/figures/model_visualizations/
/data/degraded/accuracy/
/data/degraded/completeness/
/data/degraded/consistency/
/data/degraded/timeliness/
/data/prepared/bpi2019_baseline_1000_cases.csv
/data/raw/BPI_Challenge_2019.xes
```

This means that a fresh clone of the repository will not include the raw BPI 2019 log, the prepared baseline CSV, the degraded logs, PNML models, or model visualization images.

These artifacts must either be regenerated locally or copied manually if needed.

---

## Current experimental status

The baseline experiment with 1000 cases has been successfully executed.

The following setup completed successfully:

```text
dataset: bpi2019_1000
dimension: baseline
level: 0
miner: inductive
status: ok
```

PNML model export and visualization export were also successful.

The full experiment for 1000 cases has also been executed for all three miners:

```text
Alpha Miner
Heuristics Miner
Inductive Miner
```

---

## Extended experiments on other event logs

To check whether the BPI 2019 findings generalize, the same experiment was repeated on further public event logs, with 1000 and 2000 sampled cases:

| Dataset name | Source log | Notes |
| --- | --- | --- |
| `bpi2020_domestic_declarations_1000/2000` | BPI Challenge 2020, Domestic Declarations | |
| `bpi2017_1000/2000` | BPI Challenge 2017 | `--lifecycle complete` |
| `bpi2012_1000/2000` | BPI Challenge 2012 | `--lifecycle complete` |
| `sepsis_1000` | Sepsis Cases | The log has only 1050 cases, so there is no 2000-case run |

Setup: 4 dimensions × 3 levels × 3 repetitions × 3 miners + baseline = 111 evaluations per run.

`prepare_event_log.py` is a generic version of `prepare_bpi2020.py`. The optional `--lifecycle complete` keeps only completion events, for logs that record several lifecycle transitions per activity (BPI 2012, BPI 2017). The optional `--streaming` reads only case id, activity, timestamp and lifecycle with a streaming XML parser, for logs that are too large to load with `pm4py.read_xes` (e.g. the 1.9 GB BPI 2018 log). For the logs above it produces exactly the same prepared CSV as the default reader.

Example for BPI 2017 with 2000 cases:

```powershell
$env:PYTHONHASHSEED = "0"

python experiments/process_discovery/src/prepare_event_log.py `
  --input data/raw/bpic2017.xes `
  --output data/prepared/bpi2017_baseline_2000_cases.csv `
  --max-cases 2000 `
  --random-state 42 `
  --lifecycle complete

python experiments/process_discovery/src/generate_degraded_logs.py `
  --input data/prepared/bpi2017_baseline_2000_cases.csv `
  --output-dir data/degraded/bpi2017_2000 `
  --dimensions accuracy completeness consistency timeliness `
  --levels 10 20 30 `
  --repetitions 3 `
  --random-state 42

python experiments/process_discovery/src/run_full_experiment.py `
  --baseline data/prepared/bpi2017_baseline_2000_cases.csv `
  --degraded-dir data/degraded/bpi2017_2000 `
  --dataset-name bpi2017_2000 `
  --dimensions accuracy completeness consistency timeliness `
  --levels 10 20 30 `
  --repetitions 3 `
  --fail-on-missing `
  --workers 4

python experiments/process_discovery/src/add_reconstructed_fitness.py `
  --input experiments/process_discovery/results/bpi2017_2000/metrics/discovery_results.csv
```

Results are stored in `experiments/process_discovery/results/<dataset name>/`.

### Evaluating against the original log

By default, each model is evaluated against the degraded log it was discovered from. To also measure how well it represents the real (non-degraded) process, the saved PNML models can be evaluated against the original baseline log:

```powershell
python experiments/process_discovery/src/evaluate_against_original.py `
  --dataset-name bpi2017_2000 `
  --original data/prepared/bpi2017_baseline_2000_cases.csv `
  --workers 4

python experiments/process_discovery/src/add_reconstructed_fitness.py `
  --input experiments/process_discovery/results/bpi2017_2000/metrics/discovery_results_vs_original.csv
```

The models are not discovered again, and the same evaluation code is used, so the only difference from `discovery_results.csv` is the log the models are evaluated on. The output is `discovery_results_vs_original.csv` in the same metrics folder. An interrupted run can be restarted with the same command; models that already have a result are skipped.

For BPI 2019, the models of the original 1000-case run are not stored in the repository. They were rediscovered from the same baseline and degradation settings under the dataset name `rerun_bpi2019_1000`, so that the committed BPI 2019 results are not touched.

Notes:

- `--workers N` processes N degraded logs in parallel. The results are the same as in a sequential run and are appended in the same order.
- `PYTHONHASHSEED=0` makes the results exactly reproducible. Without it, PM4Py's token replay on Heuristics Miner nets depends on Python's hash randomization, and precision/generalization can differ by up to about 0.01 between otherwise identical runs.
- Do not use `--clear-results` for these datasets: it deletes `results/metrics/discovery_results.csv`, which holds the BPI 2019 results.

---

## Notes on scalability

The BPI Challenge 2019 log is large and complex. Process discovery and replay-based evaluation can become computationally expensive, especially when running many repetitions across multiple degradation scenarios.

For this reason, the main experiment may use:

```text
1000 cases
10%, 20%, 30% degradation levels
3 or 5 repetitions
```

Larger subsets, such as 5000 cases, may be used only if computationally feasible or as supplementary validation.

A reasonable strategy is:

```text
Main experiment:
1000 cases, all degradation dimensions, all miners

Optional extended experiment:
5000 cases, selected miners or selected degradation scenarios
```

---

## Methodological summary

This experiment investigates how controlled degradation of event log quality affects process discovery results.

A prepared subset of the BPI Challenge 2019 event log is used as the baseline. Then, controlled degradation is applied to four data quality dimensions: accuracy, completeness, consistency and timeliness. For each degraded log, process discovery is performed using Alpha Miner, Heuristics Miner and Inductive Miner. The resulting Petri nets are evaluated using fitness, precision, generalization and simplicity, along with structural metrics such as the number of places, transitions and arcs.

The goal is to quantify how different types and levels of data quality degradation influence the quality and complexity of discovered process models.
