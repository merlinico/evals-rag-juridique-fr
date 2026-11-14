from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np


@dataclass(frozen=True)
class BootstrapCI:
    mean: float
    ci_low: float
    ci_high: float
    n: int
    n_boot: int
    alpha: float


@dataclass(frozen=True)
class PairedTestResult:
    """One-sided paired test: H1 = mean(current - baseline) < 0 (regression)."""

    metric: str
    mean_current: float
    mean_baseline: float
    mean_delta: float
    p_value: float
    significant: bool
    alpha: float
    test: str
    n: int
    ci_low: float | None = None
    ci_high: float | None = None


def bootstrap_ci(
    values: Sequence[float],
    *,
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
    statistic: Callable[[np.ndarray], float] | None = None,
) -> BootstrapCI:
    """Percentile bootstrap CI for the mean (or a custom statistic)."""
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return BootstrapCI(
            mean=0.0, ci_low=0.0, ci_high=0.0, n=0, n_boot=n_boot, alpha=alpha
        )
    stat = statistic or (lambda x: float(np.mean(x)))
    point = stat(arr)
    rng = np.random.default_rng(seed)
    n = arr.size
    boots = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sample = arr[rng.integers(0, n, size=n)]
        boots[i] = stat(sample)
    low = float(np.quantile(boots, alpha / 2))
    high = float(np.quantile(boots, 1 - alpha / 2))
    return BootstrapCI(
        mean=float(point),
        ci_low=low,
        ci_high=high,
        n=int(n),
        n_boot=n_boot,
        alpha=alpha,
    )


def paired_bootstrap_pvalue(
    current: Sequence[float],
    baseline: Sequence[float],
    *,
    n_boot: int = 1000,
    seed: int = 42,
) -> tuple[float, float, float, float]:
    """One-sided paired bootstrap P(mean delta >= 0) under centered null.

    Returns (mean_delta, p_value, ci_low, ci_high) for delta = current - baseline.
    Small p_value + negative mean_delta ⇒ statistically significant regression.
    """
    cur = np.asarray(list(current), dtype=float)
    base = np.asarray(list(baseline), dtype=float)
    if cur.size != base.size:
        raise ValueError("paired_bootstrap_pvalue requires equal-length series")
    if cur.size == 0:
        return 0.0, 1.0, 0.0, 0.0

    deltas = cur - base
    mean_delta = float(np.mean(deltas))
    rng = np.random.default_rng(seed)
    n = deltas.size
    # Center under H0: mean delta == 0
    centered = deltas - mean_delta
    boot_means = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sample = centered[rng.integers(0, n, size=n)]
        boot_means[i] = float(np.mean(sample))
    # One-sided: evidence for mean_delta < 0
    p_value = float(np.mean(boot_means <= mean_delta))
    p_value = min(max(p_value, 1.0 / (n_boot + 1)), 1.0)

    boot_obs = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sample = deltas[rng.integers(0, n, size=n)]
        boot_obs[i] = float(np.mean(sample))
    ci_low = float(np.quantile(boot_obs, 0.025))
    ci_high = float(np.quantile(boot_obs, 0.975))
    return mean_delta, p_value, ci_low, ci_high


def paired_regression_test(
    current: Sequence[float],
    baseline: Sequence[float],
    *,
    metric: str,
    alpha: float = 0.05,
    n_boot: int = 1000,
    seed: int = 42,
    test: str = "paired_bootstrap",
) -> PairedTestResult:
    """Fail criterion helper: significant regression iff delta < 0 and p < alpha."""
    if test != "paired_bootstrap":
        raise ValueError(f"Unsupported significance test: {test}")
    cur = list(current)
    base = list(baseline)
    mean_cur = float(np.mean(cur)) if cur else 0.0
    mean_base = float(np.mean(base)) if base else 0.0
    mean_delta, p_value, ci_low, ci_high = paired_bootstrap_pvalue(
        cur, base, n_boot=n_boot, seed=seed
    )
    significant = bool(mean_delta < 0 and p_value < alpha)
    return PairedTestResult(
        metric=metric,
        mean_current=mean_cur,
        mean_baseline=mean_base,
        mean_delta=mean_delta,
        p_value=p_value,
        significant=significant,
        alpha=alpha,
        test=test,
        n=len(cur),
        ci_low=ci_low,
        ci_high=ci_high,
    )


def align_paired_scores(
    current_ids: Sequence[str],
    current_scores: Sequence[float],
    baseline_ids: Sequence[str],
    baseline_scores: Sequence[float],
) -> tuple[list[float], list[float]]:
    """Align two per-question series on the intersection of question ids (stable order)."""
    base_map = dict(zip(baseline_ids, baseline_scores))
    cur_map = dict(zip(current_ids, current_scores))
    shared = sorted(set(cur_map) & set(base_map))
    return [cur_map[i] for i in shared], [base_map[i] for i in shared]
