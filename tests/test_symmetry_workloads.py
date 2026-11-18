from __future__ import annotations

import unittest

from benchmarking.extensions.symmetry_workloads import fixed_hamming_weight_support, make_symmetry_workload


class SymmetryWorkloadTests(unittest.TestCase):
    def test_fixed_weight_support_is_unique_and_valid(self):
        rows = fixed_hamming_weight_support(8, 4, 12, 77)
        self.assertEqual(len(rows), len(set(rows)))
        self.assertTrue(all(row.count("1") == 4 and len(row) == 8 for row in rows))

    def test_fixed_weight_generation_is_seed_deterministic(self):
        self.assertEqual(fixed_hamming_weight_support(10, 5, 20, 14), fixed_hamming_weight_support(10, 5, 20, 14))
        self.assertNotEqual(fixed_hamming_weight_support(10, 5, 20, 14), fixed_hamming_weight_support(10, 5, 20, 15))

    def test_sector_sampling_scales_without_enumerating_the_full_hilbert_space(self):
        rows = fixed_hamming_weight_support(63, 31, 7, 321)
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row.count("1") == 31 for row in rows))

    def test_invalid_n_k_s_combinations_rejected(self):
        for args in ((0, 0, 1, 1), (4, -1, 1, 1), (4, 5, 1, 1), (4, 2, 7, 1), (4, 2, 0, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                fixed_hamming_weight_support(*args)

    def test_reordering_preserves_basis_attached_amplitudes_signs_and_canonical_state(self):
        lex = make_symmetry_workload(n=10, k=5, s=12, seed=71, support_family="fixed_hamming_weight", ordering="lexicographic")
        shuffled = make_symmetry_workload(n=10, k=5, s=12, seed=71, support_family="fixed_hamming_weight", ordering="seeded_shuffled")
        self.assertEqual(lex.canonical_instance_sha256, shuffled.canonical_instance_sha256)
        self.assertNotEqual(lex.ordered_input_sha256, shuffled.ordered_input_sha256)
        attached_lex = dict(zip(lex.support, zip(lex.coefficients, lex.signs)))
        attached_shuffled = dict(zip(shuffled.support, zip(shuffled.coefficients, shuffled.signs)))
        self.assertEqual(attached_lex, attached_shuffled)

    def test_complex_norm_and_sign_profile(self):
        workload = make_symmetry_workload(n=8, k=4, s=5, seed=7, support_family="fixed_hamming_weight", coefficient_family="random_complex")
        self.assertAlmostEqual(sum(abs(x) ** 2 for x in workload.coefficients), 1.0)
        self.assertEqual(len(set(workload.signs)), 2)

    def test_random_and_fixed_weight_keep_distinct_support_and_identity(self):
        random_instance = make_symmetry_workload(n=10, s=5, seed=23, support_family="seeded_random")
        fixed_instance = make_symmetry_workload(n=10, s=5, seed=23, support_family="fixed_hamming_weight", k=5)
        self.assertNotEqual(random_instance.canonical_instance_sha256, fixed_instance.canonical_instance_sha256)
        self.assertTrue(all(row.count("1") == 5 for row in fixed_instance.support))


if __name__ == "__main__":
    unittest.main()
