from typing import Any, Dict, Tuple

import pm4py

from config import MINERS

PetriNetResult = Tuple[Any, Any, Any]

DEFAULT_HEURISTICS_PARAMS = {
    "dependency_threshold": 0.5,
    "and_threshold": 0.65,
    "loop_two_threshold": 0.5,
}


DEFAULT_INDUCTIVE_PARAMS = {
    "noise_threshold": 0.0,
}


def run_alpha_miner(log) -> PetriNetResult:
    """
    Runs the classic Alpha Miner.

    Returns:
        net, initial_marking, final_marking
    """
    return pm4py.discover_petri_net_alpha(log)


def run_heuristics_miner(
    log,
    dependency_threshold: float = 0.5,
    and_threshold: float = 0.65,
    loop_two_threshold: float = 0.5,
) -> PetriNetResult:
    """
    Runs the Heuristics Miner.

    The default thresholds are PM4Py's standard values.
    They can later be tuned if the discovered model is too complex or too restrictive.

    Returns:
        net, initial_marking, final_marking
    """
    return pm4py.discover_petri_net_heuristics(
        log,
        dependency_threshold=dependency_threshold,
        and_threshold=and_threshold,
        loop_two_threshold=loop_two_threshold,
    )


def run_inductive_miner(
    log,
    noise_threshold: float = 0.0,
) -> PetriNetResult:
    """
    Runs the Inductive Miner.

    noise_threshold = 0.0 means that no behavior is filtered as noise.
    This is useful for the first baseline run because we want to observe the raw effect
    of data quality degradation without hiding behavior too early.

    Returns:
        net, initial_marking, final_marking
    """
    return pm4py.discover_petri_net_inductive(
        log,
        noise_threshold=noise_threshold,
    )


def discover_model(
    log,
    miner_name: str,
    miner_params: Dict[str, Any] | None = None,
) -> PetriNetResult:
    """
    Runs one of the supported process discovery algorithms.

    Args:
        log:
            PM4Py EventLog or properly formatted DataFrame.
        miner_name:
            One of: alpha, heuristics, inductive.
        miner_params:
            Optional algorithm-specific parameters.

    Returns:
        net, initial_marking, final_marking
    """
    miner_name = miner_name.lower().strip()
    miner_params = miner_params or {}

    if miner_name == "alpha":
        return run_alpha_miner(log)

    if miner_name == "heuristics":
        params = DEFAULT_HEURISTICS_PARAMS.copy()
        params.update(miner_params)
        return run_heuristics_miner(log, **params)

    if miner_name == "inductive":
        params = DEFAULT_INDUCTIVE_PARAMS.copy()
        params.update(miner_params)
        return run_inductive_miner(log, **params)

    raise ValueError(
        f"Unsupported miner: {miner_name}. "
        f"Supported miners are: {MINERS}"
    )


def discover_all_models(
    log,
    miners: list[str] | None = None,
) -> Dict[str, PetriNetResult]:
    """
    Runs all selected miners on the same log.

    Args:
        log:
            PM4Py EventLog or properly formatted DataFrame.
        miners:
            Optional list of miners. If None, all supported miners are used.

    Returns:
        Dictionary:
        {
            "alpha": (net, im, fm),
            "heuristics": (net, im, fm),
            "inductive": (net, im, fm)
        }
    """
    miners = miners or MINERS

    results = {}

    for miner_name in miners:
        results[miner_name] = discover_model(log, miner_name)

    return results