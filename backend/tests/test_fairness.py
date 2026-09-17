from simulation.metrics import jain_fairness, percentile_nearest_rank


def test_jain_equal_throughputs_is_one():
    assert abs(jain_fairness([10.0, 10.0, 10.0]) - 1.0) < 1e-9


def test_jain_one_class_dominant_is_one_over_n():
    n = 4
    xs = [100.0] + [0.0] * (n - 1)
    assert abs(jain_fairness(xs) - (1.0 / n)) < 1e-9


def test_percentile_nearest_rank_basic():
    vals = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert percentile_nearest_rank(vals, 50) in (5, 6)
    assert percentile_nearest_rank(vals, 100) == 10
    assert percentile_nearest_rank(vals, 1) == 1
