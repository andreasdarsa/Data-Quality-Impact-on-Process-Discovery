from typing import Any, Dict

from pm4py.algo.evaluation import algorithm as general_evaluation


QUALITY_METRIC_KEYS = [
    "fitness",
    "precision",
    "generalization",
    "simplicity",
]


def safe_float(value: Any) -> float | None:
    """
    Converts PM4Py / numpy / Python numeric values to plain float.

    Returns None if the value is missing or cannot be converted.
    """
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_structural_metrics(net) -> Dict[str, int]:
    """
    Computes structural metrics from a Petri net.

    These metrics help us observe whether degraded data produces
    larger or more complex discovered models.
    """
    visible_transitions = [
        transition
        for transition in net.transitions
        if transition.label is not None
    ]

    hidden_transitions = [
        transition
        for transition in net.transitions
        if transition.label is None
    ]

    unique_visible_labels = {
        transition.label
        for transition in visible_transitions
    }

    duplicate_visible_labels = (
        len(visible_transitions) - len(unique_visible_labels)
    )

    return {
        "places": len(net.places),
        "transitions": len(net.transitions),
        "visible_transitions": len(visible_transitions),
        "hidden_transitions": len(hidden_transitions),
        "unique_visible_transition_labels": len(unique_visible_labels),
        "duplicate_visible_transition_labels": duplicate_visible_labels,
        "arcs": len(net.arcs),
    }


def normalize_quality_metrics(raw_metrics: Dict[str, Any]) -> Dict[str, float | None]:
    """
    Normalizes the metric dictionary returned by PM4Py.

    Expected PM4Py keys usually include:
    - fitness
    - precision
    - generalization
    - simplicity

    Depending on PM4Py version, the average metric key may vary,
    so we check multiple possible names.
    """
    normalized = {}

    for key in QUALITY_METRIC_KEYS:
        normalized[key] = safe_float(raw_metrics.get(key))

    average_candidates = [
        "metricsAverageWeight",
        "average_metric",
        "average",
        "average_score",
    ]

    average_score = None

    for candidate in average_candidates:
        if candidate in raw_metrics:
            average_score = safe_float(raw_metrics.get(candidate))
            break

    normalized["average_score"] = average_score

    return normalized


def evaluate_quality_metrics(
    log,
    net,
    initial_marking,
    final_marking,
) -> Dict[str, float | None]:
    """
    Evaluates a discovered Petri net against an event log.

    Returns:
        Dictionary with:
        - fitness
        - precision
        - generalization
        - simplicity
        - average_score
    """
    raw_metrics = general_evaluation.apply(
        log,
        net,
        initial_marking,
        final_marking,
    )

    return normalize_quality_metrics(raw_metrics)


def evaluate_model(
    log,
    net,
    initial_marking,
    final_marking,
) -> Dict[str, Any]:
    """
    Computes all evaluation metrics for a discovered model.

    Includes:
    - PM4Py quality metrics
    - structural Petri net metrics
    """
    quality_metrics = evaluate_quality_metrics(
        log=log,
        net=net,
        initial_marking=initial_marking,
        final_marking=final_marking,
    )

    structural_metrics = get_structural_metrics(net)

    return {
        **quality_metrics,
        **structural_metrics,
    }
