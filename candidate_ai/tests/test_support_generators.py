from sparseprep.support_generators import (
    partial_final_batch_problem, random_problem, random_support,
    support_inside_subspace, support_with_repeated_prefix,
)


def test_random_support_is_deterministic_and_distinct():
    a = random_support(10, 20, 42)
    assert a == random_support(10, 20, 42)
    assert len(set(a)) == 20
    assert all(len(x) == 10 for x in a)


def test_support_inside_subspace_has_zero_residual_suffix():
    p = support_inside_subspace(7, 5, seed=8)
    assert len(set(p.support)) == p.s
    assert all(x[p.ell:] == "0" * p.residual_width for x in p.support)


def test_repeated_prefix_family():
    p = support_with_repeated_prefix(8, 4, seed=3)
    assert len(set(p.support)) == 4
    assert len({x[:p.ell] for x in p.support}) == 1


def test_partial_final_batch_metadata():
    p = partial_final_batch_problem(8, 7, batch_size=4, seed=11)
    assert p.metadata_dict["remainder"] == "3"


def test_random_problem_metadata():
    p = random_problem(5, 3, 123)
    assert p.seed == 123
    assert p.metadata_dict["family"] == "seeded-random"
