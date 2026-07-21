"""Plot-scale helpers."""

import numpy as np
import pytest

from radcoolpv.plotting.figures import _positive_y_limit


def test_positive_y_limit_adds_ten_percent_headroom():
    assert _positive_y_limit(np.array([-2.0, 4.0]), np.array([3.0])) == pytest.approx(4.4)


def test_positive_y_limit_has_a_safe_fallback():
    assert _positive_y_limit(np.array([-2.0, 0.0])) == pytest.approx(1.0)
