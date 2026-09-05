import pytest

from mcx_project.uncertainty import replicate_summary, endpoint_gate, qualified_ratio


def test_low_signal_ratio_is_suppressed_even_when_repeatable():
    criteria = {"minimum_absorbed_fraction": 1e-8, "max_cv": .05, "max_relative_change": .1}
    tiny = replicate_summary([1e-10, 1e-10, 1e-10])
    stable = replicate_summary([1e-3, 1.001e-3, .999e-3])
    bad = endpoint_gate(tiny, tiny, tiny, 1e-10, criteria)
    good = endpoint_gate(stable, stable, stable, 1e-3, criteria)
    assert good["qualified"]
    assert not bad["qualified"]
    assert qualified_ratio(stable, tiny, good, bad)["ratio"] is None
    assert qualified_ratio(stable, stable, good, good)["ratio"] == pytest.approx(1)


def test_noisy_or_time_unstable_endpoints_fail():
    criteria = {"minimum_absorbed_fraction": 1e-8, "max_cv": .05, "max_relative_change": .1}
    stable = replicate_summary([1,1,1])
    noisy = replicate_summary([.5,1,1.5])
    extended = replicate_summary([1.5,1.5,1.5])
    assert not endpoint_gate(stable, noisy, stable, 1, criteria)["qualified"]
    assert not endpoint_gate(stable, stable, extended, 1, criteria)["checks"]["time_window_stability"]
