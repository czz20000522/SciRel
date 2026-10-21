import inspect

from scirel.inference.latin_hypercube_sampling import sample_latin_hypercube


def test_public_callable_documents_the_catalog_contract():
    text = inspect.getdoc(sample_latin_hypercube) or ""
    assert "bounds" in text
    assert "initial_samples" in text
    assert "ValueError" in text


def test_seeded_strata():
    first = sample_latin_hypercube(bounds={'a': (0.0, 1.0)}, n_samples=5, seed=4)['initial_samples']
    second = sample_latin_hypercube(bounds={'a': (0.0, 1.0)}, n_samples=5, seed=4)['initial_samples']
    assert first == second
    assert sorted(int(row['a'] * 5) for row in first) == [0, 1, 2, 3, 4]


def test_reviewed_relation_example():
    from scirel.inference.latin_hypercube_sampling import sample_latin_hypercube

    bounds = {"a": (0.0, 1.0), "b": (10.0, 20.0)}
    first = sample_latin_hypercube(bounds=bounds, n_samples=5, seed=4)["initial_samples"]
    second = sample_latin_hypercube(bounds=bounds, n_samples=5, seed=4)["initial_samples"]
    assert first == second
    assert all(0.0 <= row["a"] < 1.0 and 10.0 <= row["b"] < 20.0 for row in first)
    assert sorted(int(row["a"] * 5.0) for row in first) == [0, 1, 2, 3, 4]
    assert sorted(int((row["b"] - 10.0) / 10.0 * 5.0) for row in first) == [0, 1, 2, 3, 4]
    subset = sample_latin_hypercube(bounds=bounds, n_samples=2, seed=1, fit_keys=["b"])["initial_samples"]
    assert all(set(row) == {"b"} for row in subset)

    for bad_call in (
        lambda: sample_latin_hypercube(bounds=bounds, n_samples=0, seed=1),
        lambda: sample_latin_hypercube(bounds={"a": (1.0, 1.0)}, n_samples=2, seed=1),
        lambda: sample_latin_hypercube(bounds={"a": (0.0, float("inf"))}, n_samples=2, seed=1),
    ):
        try:
            bad_call()
        except ValueError:
            pass
        else:
            raise AssertionError("非法样本数或边界必须失败")


def test_boolean_sample_count_is_rejected_as_value_error():
    import pytest

    with pytest.raises(ValueError, match="positive integer n_samples"):
        sample_latin_hypercube(bounds={"a": (0.0, 1.0)}, n_samples=True)
