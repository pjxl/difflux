from difflux.format import churn_bar, _FILLED, _TRACK


def test_zero_max_is_all_track():
    assert churn_bar(0, 0, width=8) == _TRACK * 8
    assert churn_bar(5, 0, width=8) == _TRACK * 8


def test_zero_value_is_all_track():
    assert churn_bar(0, 100, width=8) == _TRACK * 8


def test_max_value_fills_full_width():
    assert churn_bar(100, 100, width=8) == _FILLED * 8


def test_nonzero_value_fills_at_least_one_cell():
    bar = churn_bar(1, 1000, width=8)
    assert bar[0] == _FILLED
    assert bar.count(_FILLED) == 1


def test_fill_is_monotonic_in_value():
    fills = [churn_bar(v, 1000, width=8).count(_FILLED) for v in (10, 100, 400, 1000)]
    assert fills == sorted(fills)
    assert fills[0] >= 1 and fills[-1] == 8


def test_sqrt_scale_separates_midrange_under_a_dominant_outlier():
    # Linear scaling would flatten all of these to 1 cell against max=592.
    cfg = churn_bar(15, 592, width=8).count(_FILLED)
    log = churn_bar(52, 592, width=8).count(_FILLED)
    retry = churn_bar(108, 592, width=8).count(_FILLED)
    assert cfg < log < retry


def test_value_above_max_clamps_to_full():
    assert churn_bar(200, 100, width=8) == _FILLED * 8


def test_fixed_width_always():
    for v in (0, 1, 37, 99, 500):
        assert len(churn_bar(v, 100, width=8)) == 8
