"""Prospective endpoint checks for a bounded Monte Carlo audit."""

import numpy as np
from scipy import ndimage, stats


def depth_masks(labels):
    background = labels == 0
    border = np.zeros(labels.shape, dtype=bool)
    border[[0,-1],:,:] = background[[0,-1],:,:]
    border[:,[0,-1],:] = background[:,[0,-1],:]
    border[:,:,[0,-1]] = background[:,:,[0,-1]]
    exterior = ndimage.binary_propagation(border, mask=background)
    depth = ndimage.distance_transform_edt(~exterior)
    masks = {"gray_matter": labels == 2, "white_matter": labels == 3,
             "brain": np.isin(labels, [2,3])}
    for tissue in ("gray_matter", "white_matter", "brain"):
        for low, high in zip([0,10,20,30,40,50], [10,20,30,40,50,np.inf]):
            masks[f"{tissue}__depth_{low}_{high}_mm"] = masks[tissue] & (depth >= low) & (depth < high)
    return masks


def replicate_summary(values):
    values = np.asarray(values, dtype=float)
    if values.size < 3 or not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("at least three finite nonnegative independent replicates required")
    mean = float(values.mean())
    sd = float(values.std(ddof=1))
    half_width = float(stats.t.ppf(.975, values.size - 1) * sd / np.sqrt(values.size))
    return {"n": int(values.size), "mean": mean, "sd": sd,
            "cv": sd / mean if mean > 0 else None,
            "ci95_low": max(0., mean - half_width), "ci95_high": mean + half_width}


def endpoint_gate(low, high, extended, baseline, criteria):
    mean = high["mean"]
    change = lambda value: abs(value - mean) / mean if mean > 0 else None
    checks = {
        "minimum_signal": mean >= criteria["minimum_absorbed_fraction"],
        "replicate_cv": high["cv"] is not None and high["cv"] <= criteria["max_cv"],
        "ci_excludes_zero": high["ci95_low"] > 0,
        "photon_count_stability": mean > 0 and change(low["mean"]) <= criteria["max_relative_change"],
        "time_window_stability": mean > 0 and change(extended["mean"]) <= criteria["max_relative_change"],
        "saved_basis_agreement": mean > 0 and change(baseline) <= criteria["max_relative_change"],
    }
    return {"qualified": all(checks.values()), "checks": checks,
            "photon_count_relative_change": change(low["mean"]),
            "time_window_relative_change": change(extended["mean"]),
            "saved_basis_relative_change": change(baseline)}


def qualified_ratio(numerator, denominator, numerator_gate, denominator_gate):
    qualified = numerator_gate["qualified"] and denominator_gate["qualified"] and denominator["ci95_low"] > 0
    return {"qualified": qualified,
            "numerator_mean": numerator["mean"], "denominator_mean": denominator["mean"],
            "ratio": numerator["mean"] / denominator["mean"] if qualified else None,
            "interval_from_marginal_ci95": [numerator["ci95_low"] / denominator["ci95_high"],
                                          numerator["ci95_high"] / denominator["ci95_low"]] if qualified else None,
            "interval_note": "Range from separate marginal 95% Student-t mean intervals; not a joint 95% ratio confidence interval."}
