# The Impact of Data Quality on Process Discovery

## 1. Project Overview

This repository contains the experimental implementation of the process discovery part of a thesis investigating how data quality degradation affects the quality and structure of discovered business process models.

The main objective is to examine how different types and levels of event log degradation influence the Petri nets discovered by process mining algorithms.

The experiments focus on four data quality dimensions:

- **Accuracy**
- **Completeness**
- **Consistency**
- **Timeliness**

Discovered process models are evaluated using four quality metrics:

- Fitness
- Precision
- Generalization
- Simplicity

In addition, structural properties of the discovered Petri nets are measured, including the number of places, transitions, visible and hidden transitions, and arcs.

The repository also includes extended experiments on multiple public event logs and an analysis comparing model evaluation against degraded logs and the original, non-degraded reference log.

---

## 2. Experimental Methodology

The general experimental workflow consists of the following stages:

```text
Original XES Event Log
        |
        v
Event Log Preparation
        |
        v
Baseline Case Sampling
        |
        v
Controlled Data Quality Degradation
        |
        v
Process Discovery
        |
        v
Petri Net Evaluation
        |
        v
Structural Analysis
        |
        v
Aggregation and Visualization
```

### 2.1 Event Log Preparation

Original XES event logs are converted into a common tabular representation containing:

- `case_id`
- `activity`
- `complete_timestamp`
- `event_index`

Depending on the source log, additional preprocessing may be applied, such as filtering lifecycle transitions.

A reproducible subset of cases is selected using a fixed random seed.

### 2.2 Data Quality Degradation

Controlled degradation is applied to the prepared baseline event log.

Each degradation scenario is defined by:

- A data quality dimension.
- A degradation level.
- A repetition identifier.

The original baseline remains unchanged. Each degraded log is saved separately and accompanied by metadata describing the applied transformation.

### 2.3 Process Discovery

Three process discovery algorithms are evaluated:

- Alpha Miner
- Heuristics Miner
- Inductive Miner

Each algorithm discovers a Petri net from the corresponding baseline or degraded event log.

The resulting models are exported in PNML format. Model visualizations can also be generated.

### 2.4 Model Evaluation

Each discovered Petri net is evaluated against the event log from which it was discovered.

An additional evaluation procedure is available for comparing the discovered models against the original, non-degraded baseline log.

This distinction is important: evaluating a model against its own degraded discovery log measures how well it represents that degraded log, whereas evaluation against the original log examines how well it represents the reference process.

The additional evaluation does not rediscover the models. It loads the previously exported PNML files and evaluates them against the original event log.

---

## 3. Data Quality Dimensions

Four degradation dimensions are implemented.

| Dimension | Description | Examples |
|---|---|---|
| Accuracy | Incorrectly recorded information | Wrong activity labels, incorrect case assignment |
| Completeness | Missing information | Event removal |
| Consistency | Inconsistent representation of information | Activity label variations, duplicate events |
| Timeliness | Incorrect event recording times | Timestamp shifts and timestamp swaps within a case |

The exact degradation operators are implemented in `experiments/process_discovery/src/degradation.py`.

### 3.1 Accuracy

Accuracy degradation simulates incorrectly recorded event information.

Examples include incorrect activity labels and incorrect case assignments.

Timestamp-related errors are handled separately under timeliness.

### 3.2 Completeness

Completeness degradation simulates missing event information by removing events from the original log.

### 3.3 Consistency

Consistency degradation introduces inconsistencies in the representation of event information.

Examples include variations in activity labels and duplicate events.

### 3.4 Timeliness

Timeliness degradation simulates problems in the temporal recording of events.

The implemented mechanisms include timestamp shifts and timestamp swaps within the same case.

**Timestamp handling:** The BPI Challenge 2019 event log provides only a completion timestamp (`time:timestamp`). It is mapped to `complete_timestamp`. No artificial `start_timestamp` is created or used. Timeliness degradation therefore operates exclusively on `complete_timestamp`.

---

## 4. Datasets

The repository includes experiments on five public event log sources.

### 4.1 BPI Challenge 2019

BPI Challenge 2019 is the primary dataset used in the initial process discovery experiment.

The prepared baseline subsets contain 1,000 or 2,000 cases, depending on the experiment.

The original XES file is expected at:

```text
data/raw/BPI_Challenge_2019.xes
```

The dedicated preparation script is:

```text
experiments/process_discovery/src/prepare_bpi2019.py
```

### 4.2 BPI Challenge 2020 — Domestic Declarations

The extended experiments include the Domestic Declarations event log from BPI Challenge 2020.

Prepared subsets of 1,000 and 2,000 cases are used.

### 4.3 BPI Challenge 2017

The BPI Challenge 2017 event log is included in the extended experiments.

Only events with the `complete` lifecycle transition are retained during preparation:

```text
--lifecycle complete
```

This ensures that the prepared event log focuses on completed activities.

### 4.4 BPI Challenge 2012

The BPI Challenge 2012 event log is also included in the extended experiments.

As with BPI 2017, the preparation procedure can retain only completed lifecycle transitions.

### 4.5 Sepsis Cases

The Sepsis Cases event log is used as an additional validation dataset.

The available log contains approximately 1,050 cases, so only the 1,000-case experiment is included.

### Dataset overview

| Dataset | Sample sizes |
|---|---|
| BPI Challenge 2019 | 1,000 and 2,000 |
| BPI Challenge 2020 — Domestic Declarations | 1,000 and 2,000 |
| BPI Challenge 2017 | 1,000 and 2,000 |
| BPI Challenge 2012 | 1,000 and 2,000 |
| Sepsis Cases | 1,000 |

The raw XES files are not included in the repository and must be obtained separately.

---

## 5. Experimental Configuration

The main configuration is defined in:

```text
experiments/process_discovery/src/config.py
```

Default settings for the primary BPI 2019 experiment:

```python
MINERS = [
    "alpha",
    "heuristics",
    "inductive",
]

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

### 5.1 Primary BPI 2019 experiment

The full experiment includes:

| Scenario | Configurations |
|---|---:|
| Baseline | 1 |
| 4 dimensions × 3 levels × 5 repetitions | 60 |
| **Total log configurations** | **61** |

Each configuration is evaluated using all three miners.

Therefore:

```text
Baseline:
1 × 3 = 3 evaluations

Degraded:
4 × 3 × 5 × 3 = 180 evaluations

Total:
183 evaluations
```

### 5.2 Extended experiments

The extended experiments use:

- Four degradation dimensions.
- Three degradation levels: 10%, 20%, and 30%.
- Three repetitions.
- Three process discovery algorithms.
- One baseline evaluation per miner.

This results in:

```text
4 × 3 × 3 × 3 + 3 = 111 evaluations
```

per dataset and sample-size configuration.

The extended experiments cover four datasets at both 1,000 and 2,000 cases, and the Sepsis dataset at 1,000 cases.

---

## 6. Evaluation Metrics

### 6.1 Process Model Quality

The discovered Petri nets are evaluated using the following metrics:

| Metric | Purpose |
|---|---|
| Fitness | Measures how well the model can reproduce the observed behavior in the event log |
| Precision | Measures how much behavior allowed by the model is supported by the event log |
| Generalization | Estimates the model's ability to represent behavior beyond the observed traces |
| Simplicity | Measures the simplicity of the discovered model |

An aggregate score is also recorded when provided by the PM4Py evaluation procedure.

### 6.2 Structural Petri Net Metrics

The following structural properties are extracted:

- Number of places.
- Number of transitions.
- Number of visible transitions.
- Number of hidden transitions.
- Number of unique visible transition labels.
- Number of duplicate visible transition labels.
- Number of arcs.

These measurements help investigate whether data degradation leads to changes in the size and structural complexity of discovered models.

### 6.3 Evaluation Against the Original Log

The extended evaluation procedure compares two perspectives:

1. **Observed evaluation:** Each model is evaluated against the degraded log from which it was discovered.
2. **Reference evaluation:** The same model is evaluated against the original, non-degraded baseline log.

This allows the analysis to distinguish between a model that fits the degraded observations and a model that continues to represent the original process.

The comparison is implemented in:

```text
experiments/process_discovery/src/dual_log_analysis.py
experiments/process_discovery/src/evaluate_against_original.py
```

---

## 7. Repository Structure

The main implementation is located in:

```text
experiments/process_discovery/
```

Its structure is:

```text
experiments/
└── process_discovery/
    ├── src/
    │   ├── config.py
    │   ├── prepare_bpi2019.py
    │   ├── prepare_bpi2020.py
    │   ├── prepare_event_log.py
    │   ├── degradation.py
    │   ├── generate_degraded_logs.py
    │   ├── discovery.py
    │   ├── evaluation.py
    │   ├── run_discovery_experiment.py
    │   ├── run_full_experiment.py
    │   ├── evaluate_against_original.py
    │   ├── add_reconstructed_fitness.py
    │   ├── degradation_mechanisms.py
    │   ├── dual_log_analysis.py
    │   ├── paper_figures.py
    │   └── plots.py
    │
    └── results/
        ├── metrics/
        ├── models/
        └── figures/
```

Additional notebooks are available for inspecting and summarizing experimental results.

---

## 8. Installation

The experiments were developed using Python 3.11.

From the repository root, create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```bash
python -m pip install --upgrade pip
pip install pm4py pandas numpy matplotlib tqdm openpyxl graphviz
```

Graphviz may also require a separate system-level installation, depending on the operating system.

---

## 9. Execution

All commands below are executed from the repository root.

### 9.1 Prepare the BPI 2019 baseline

Place the original XES file at:

```text
data/raw/BPI_Challenge_2019.xes
```

Generate a prepared subset of 1,000 cases:

```powershell
python experiments/process_discovery/src/prepare_bpi2019.py `
  --input data/raw/BPI_Challenge_2019.xes `
  --output data/prepared/bpi2019_baseline_1000_cases.csv `
  --max-cases 1000
```

### 9.2 Generate degraded logs

```powershell
python experiments/process_discovery/src/generate_degraded_logs.py `
  --input data/prepared/bpi2019_baseline_1000_cases.csv `
  --output-dir data/degraded/bpi2019_1000 `
  --dimensions accuracy completeness consistency timeliness `
  --levels 10 20 30 `
  --repetitions 5
```

The script generates the degraded logs and a `degradation_manifest.csv` containing metadata for each generated configuration.

### 9.3 Run the full process discovery experiment

```powershell
python experiments/process_discovery/src/run_full_experiment.py `
  --baseline data/prepared/bpi2019_baseline_1000_cases.csv `
  --degraded-dir data/degraded/bpi2019_1000 `
  --dataset-name bpi2019_1000 `
  --clear-results
```

To execute a smaller test run using only the Inductive Miner:

```powershell
python experiments/process_discovery/src/run_full_experiment.py `
  --baseline data/prepared/bpi2019_baseline_1000_cases.csv `
  --degraded-dir data/degraded/bpi2019_1000 `
  --dataset-name bpi2019_1000 `
  --miners inductive `
  --levels 10 `
  --repetitions 1 `
  --clear-results
```

### 9.4 Run the extended experiments

For other event logs, use the generic preparation script:

```powershell
python experiments/process_discovery/src/prepare_event_log.py `
  --input data/raw/bpic2017.xes `
  --output data/prepared/bpi2017_baseline_2000_cases.csv `
  --max-cases 2000 `
  --random-state 42 `
  --lifecycle complete
```

For logs that are too large to load into memory using PM4Py, the optional `--streaming` flag enables a streaming XML parser that reads only the required event attributes.

Generate degraded logs:

```powershell
python experiments/process_discovery/src/generate_degraded_logs.py `
  --input data/prepared/bpi2017_baseline_2000_cases.csv `
  --output-dir data/degraded/bpi2017_2000 `
  --dimensions accuracy completeness consistency timeliness `
  --levels 10 20 30 `
  --repetitions 3 `
  --random-state 42
```

Run the experiment:

```powershell
python experiments/process_discovery/src/run_full_experiment.py `
  --baseline data/prepared/bpi2017_baseline_2000_cases.csv `
  --degraded-dir data/degraded/bpi2017_2000 `
  --dataset-name bpi2017_2000 `
  --dimensions accuracy completeness consistency timeliness `
  --levels 10 20 30 `
  --repetitions 3 `
  --fail-on-missing `
  --workers 4
```

The same workflow can be applied to the other supported event logs by changing the input, output and dataset names.

### 9.5 Evaluate discovered models against the original log

After the discovery experiment has generated and saved the PNML models:

```powershell
python experiments/process_discovery/src/evaluate_against_original.py `
  --dataset-name bpi2017_2000 `
  --original data/prepared/bpi2017_baseline_2000_cases.csv `
  --workers 4
```

To calculate reconstructed fitness:

```powershell
python experiments/process_discovery/src/add_reconstructed_fitness.py `
  --input experiments/process_discovery/results/bpi2017_2000/metrics/discovery_results_vs_original.csv
```

The evaluation can be resumed after interruption. Models that already have a result are skipped.

**Important:** Do not use `--clear-results` when running additional datasets if doing so would remove previously stored results. In particular, the original BPI 2019 results are stored in the default results directory.

---

## 10. Analysis and Visualization

### 10.1 Standard experiment plots

After completing the discovery experiments, generate plots using:

```powershell
python experiments/process_discovery/src/plots.py `
  --input experiments/process_discovery/results/metrics/discovery_results.csv `
  --output-dir experiments/process_discovery/results/figures
```

The plotting script produces visual comparisons of the process model quality and structural metrics across degradation scenarios.

### 10.2 Degradation mechanism analysis

The `degradation_mechanisms.py` script examines the effect of degradation directly on the event logs, independently of process discovery.

It measures:

- Change in the number of distinct activities.
- Change in the number of distinct directly-follows relations.
- Share of novel directly-follows relations.
- Share of lost directly-follows relations.
- Change in the number of trace variants.
- Change in mean trace length.
- Share of cases whose activity sequence changed.

### 10.3 Dual-log analysis and paper figures

The extended analysis compares observed and reference evaluation results.

The `paper_figures.py` script generates publication-oriented figures, LaTeX tables and summary statistics from the analysis outputs.

Its expected inputs include:

```text
results/dual_log_analysis/cells.csv
results/dual_log_analysis/instances.csv
results/paper/degradation_mechanisms.csv
```

The generated outputs include:

```text
results/paper/
├── fig_dual_evaluation_30.pdf
├── fig_gap_by_level.pdf
├── tab_mechanisms.tex
├── tab_complexity.tex
└── paper_stats.txt
```

---

## 11. Results and Generated Artifacts

The experiment generates several types of outputs.

### Metrics

The main results file is:

```text
experiments/process_discovery/results/metrics/discovery_results.csv
```

For dataset-specific extended experiments, results are stored under:

```text
experiments/process_discovery/results/<dataset_name>/metrics/
```

The results contain one row per evaluated model and configuration.

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
average_score
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

### Petri net models

Discovered models are exported in PNML format under:

```text
experiments/process_discovery/results/models/pnml/
```

Dataset-specific experiments use their corresponding results directory.

### Figures

Generated visualizations are stored under:

```text
experiments/process_discovery/results/figures/
```

### Prepared and degraded data

Local data artifacts are stored under:

```text
data/
├── raw/
├── prepared/
└── degraded/
```

Raw event logs, prepared subsets, degraded logs, PNML models and generated figures may be excluded from version control because of their size.

They can be regenerated using the corresponding scripts, provided that the original XES files are available.

---

## 12. Reproducibility Notes

The experiments use fixed random seeds for reproducible case sampling and degradation generation.

For the extended experiments, setting the following environment variable is recommended:

```powershell
$env:PYTHONHASHSEED = "0"
```

This is particularly relevant for Heuristics Miner evaluation, where PM4Py token replay can depend on Python hash randomization. Without a fixed hash seed, precision and generalization may differ slightly between otherwise identical runs.

The `--workers` option allows degraded logs to be processed in parallel. The results are intended to be equivalent to sequential execution.

For interrupted experiments, the same command can be used to resume processing where supported by the experiment runner.

---

## 13. Limitations

The experimental findings should be interpreted in light of the following limitations:

- The experiments use sampled subsets of the original event logs rather than necessarily processing every available case.
- The degradation operators represent controlled approximations of data quality problems and may not cover every type of recording imperfection found in operational systems.
- Different event logs have different activity vocabularies, lifecycle conventions, sizes and process characteristics.
- The availability of event attributes and lifecycle information varies across datasets.
- The evaluation metrics capture different aspects of model quality and should not be interpreted independently of the event log used for evaluation.
- Process discovery algorithms may respond differently to changes in event frequency, trace variants and directly-follows relations.

---

## 14. Project Scope

This repository focuses exclusively on the **process discovery** component of the broader study of data quality in business process event logs.

A separate repository implements the anomaly detection experiments:

[Data Quality Impact on Business Process Anomaly Detection](https://github.com/andreasdarsa/Data-Quality-Impact-on-Business-Process-Anomaly-Detection)

The two repositories address complementary aspects of the same research problem:

- Process discovery: how data quality degradation affects the discovered process models.
- Anomaly detection: how data quality degradation affects the identification of anomalous process executions.

They are maintained independently to preserve the distinction between their datasets, experimental configurations and evaluation pipelines.

---

## Data Sources

The event logs used in this project originate from publicly available process mining benchmarks and datasets, including the BPI Challenges and the Sepsis Cases event log.

Users are responsible for obtaining the original event logs from their respective sources and complying with the applicable data access and usage conditions.
