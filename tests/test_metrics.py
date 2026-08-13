import numpy as np
import pytest

from mcx_project.metrics import contribution_metrics, reference_source_enhancement


def test_contribution_metrics_hand_computable() -> None:
    contributions = np.array([[1.0, 3.0, 0.0], [1.0, 1.0, 0.0]])
    metrics = contribution_metrics(contributions)

    np.testing.assert_allclose(metrics["total"], [2.0, 4.0, 0.0])
    np.testing.assert_allclose(metrics["ef_dom"][:2], [2.0, 4.0 / 3.0])
    np.testing.assert_allclose(
        metrics["non_dominant_contribution_fraction"][:2], [0.5, 0.25]
    )
    np.testing.assert_allclose(metrics["n_eff"][:2], [2.0, 1.6])
    assert np.isnan(metrics["ef_dom"][2])
    assert not metrics["valid_mask"][2]


def test_reference_source_enhancement_is_not_dominant_enhancement() -> None:
    contributions = np.array([[1.0, 1.0], [3.0, 1.0]])
    result = reference_source_enhancement(contributions, 0)
    np.testing.assert_allclose(result, [4.0, 2.0])


def test_metrics_reject_negative_contributions() -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        contribution_metrics([[1.0], [-1.0]])


def test_near_zero_threshold_masks_both_metric_definitions() -> None:
    contributions = np.array([[1e-14, 2.0], [2e-14, 1.0]])
    metrics = contribution_metrics(contributions, threshold=1e-12)
    reference = reference_source_enhancement(
        contributions, reference_source=0, threshold=1e-12
    )

    assert not metrics["valid_mask"][0]
    assert np.isnan(metrics["ef_dom"][0])
    assert np.isnan(metrics["non_dominant_contribution_fraction"][0])
    assert np.isnan(metrics["n_eff"][0])
    assert np.isnan(reference[0])
    assert metrics["valid_mask"][1]
    assert reference[1] == pytest.approx(1.5)


def test_total_threshold_for_ncf_is_distinct_from_dominant_threshold() -> None:
    metrics = contribution_metrics([[0.6], [0.6]], threshold=1.0)
    assert not metrics["ef_dom_valid_mask"][0]
    assert metrics["total_valid_mask"][0]
    assert np.isnan(metrics["ef_dom"][0])
    assert metrics["non_dominant_contribution_fraction"][0] == pytest.approx(0.5)
    assert metrics["n_eff"][0] == pytest.approx(2.0)
