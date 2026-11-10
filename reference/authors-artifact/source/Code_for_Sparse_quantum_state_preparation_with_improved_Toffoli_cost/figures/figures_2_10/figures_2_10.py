# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

import rsmf
import numpy as np
import time

import matplotlib.gridspec as gridspec

from qualtran.resource_counting import QECGatesCost, get_cost_value

from sparse_state_preparation import (
    find_bijection_and_circuit,
    fast_toffoli_counter,
    random_signs,
    random_tableau,
    IsometryToSubspaceViaBatching,
)

seed = 236246247457


def log2ceil(d: int) -> int:
    """
    Ceiling of log_2(d).
    """
    return np.ceil(np.log2(d))


def ns_selected(d: int) -> list[int]:
    """
    For d rows give a list of ns, where n is the number of columns.
    Make sure that all ns are big enough such that there can be d
    unique rows.
    """
    start = int(log2ceil(d) + 2)
    first_3 = start + 5  # should have first 2 steps

    steps = [start + (1 << i) for i in range(3, 10)]
    around = lambda s: list(range(s - 3, s - 1))
    return list(range(start, first_3)) + sum([around(s) for s in steps], [])


def toffoli_cost(cost):
    """
    Count the Toffoli gates.
    """
    return cost.and_bloq + cost.cswap


def get_toffoli(d: int, n: int) -> tuple[int, int, float, float]:
    """
    Given a number of rows ``d`` and a number of columns ``n`` get a random
    tableau and signs, apply the isometry algorithm to the restricted
    and unrestricted algorithm. Collect the number of Toffolis needed
    and the wallclock time required for running the algorithm.

    Return ``(Toffolis unrestricted, Toffolis restrictd, time unrestricted, time restricted)``.
    """
    tableau = random_tableau(d, n, seed=seed)
    signs = random_signs(d, seed=seed)

    if d == 10**6:
        sub_problem_size = 20
    elif d == 10**7:
        sub_problem_size = 80
    else:
        sub_problem_size = None

    start = time.perf_counter()
    _, circuit_unrest = find_bijection_and_circuit(tableau, None, sub_problem_size)
    time_unrestricted = time.perf_counter() - start
    _, circuit_rest = find_bijection_and_circuit(tableau, signs, sub_problem_size)
    time_restricted = time.perf_counter() - start - time_unrestricted

    a, b = fast_toffoli_counter(circuit_unrest), fast_toffoli_counter(circuit_rest)

    if d == 100:
        # Treat d=100 extra as otherwise bounding errors from fast_toffoli_counter will lead to a jump after n=80.
        iso = IsometryToSubspaceViaBatching(tableau)
        a = toffoli_cost(get_cost_value(iso, QECGatesCost()))
        iso = IsometryToSubspaceViaBatching(tableau, signs)
        b = toffoli_cost(get_cost_value(iso, QECGatesCost()))
    print(d, n, a, b, time_unrestricted, time_restricted)
    return a, b, time_unrestricted, time_restricted


def isometry_cost_malvetti_bound(d: int, n: int) -> int:
    """
    Compute an upper bound on the number of Toffolis required
    for running the isometry algorithm of Malvetti et. al [https://quantum-journal.org/papers/q-2021-03-15-412/].
    """
    assert n > log2ceil(d)
    return int(d * (log2ceil(d) - 1))


def isometry_cost_us_bound(d: int, n: int) -> int:
    """
    Compute an upper bound on the number of Toffolis required
    for running our isometry algorithm.
    """
    assert n > log2ceil(d)
    m = 2 ** np.floor(np.log2(n - log2ceil(d)))
    return int(
        np.ceil(d / m) * (2 * m + 0.5 * (log2ceil(d) - np.log2(m)) - 3)
        + (2 * log2ceil(d) - np.log2(m))  # equation (1)
    )


def ns(d: int) -> list[int]:
    """
    For d rows give a list of ns, where n is the number of columns.
    Make sure that all ns are big enough such that there can be d
    unique rows.
    """
    return range(int(log2ceil(d) + 1), 5 * 10**3)


# Collect data

toffoli_quotients_unrest = {}
toffoli_quotients_rest = {}
wallclock_times_unrest = {}
wallclock_times_rest = {}
wallclock_times_unrest_avg = {}
wallclock_times_rest_avg = {}

for j in range(2, 8):
    d = 10**j
    toffolis = [get_toffoli(d, n) for n in ns_selected(d)]
    toffoli_quotients_unrest[j] = [toff[0] / d for toff in toffolis]
    toffoli_quotients_rest[j] = [toff[1] / d for toff in toffolis]
    wallclock_times_unrest[j] = [toff[2] for toff in toffolis]
    wallclock_times_rest[j] = [toff[3] for toff in toffolis]
    wallclock_times_unrest_avg[j] = sum(toff[2] for toff in toffolis) / len(toffolis)
    wallclock_times_rest_avg[j] = sum(toff[3] for toff in toffolis) / len(toffolis)

# Print for reference

print("Quotients (unrestricted)", toffoli_quotients_unrest)
print("Quotients (restricted)", toffoli_quotients_rest)
print("Times (unrestricted):", wallclock_times_unrest)
print("Times (restricted):", wallclock_times_rest)
print("Avg. times (unrestricted):", wallclock_times_unrest_avg)
print("Avg. times (restricted):", wallclock_times_rest_avg)

# Create figure 2
formatter = rsmf.setup(
    r"\documentclass[onecolumn, a4paper, unpublished]{quantumarticle}"
)
fig = formatter.figure(aspect_ratio=0.3, width_ratio=1.13)
gs = gridspec.GridSpec(nrows=1, ncols=2, figure=fig, width_ratios=[1, 1], wspace=0.3)

ax_left = fig.add_subplot(gs[0, 0])
ax_right = fig.add_subplot(gs[0, 1])

# Left plot

# Create data for plot
for j in range(2, 9):
    d = 10**j
    improvement_factors = [
        isometry_cost_malvetti_bound(d, n) / isometry_cost_us_bound(d, n) for n in ns(d)
    ]

    best_n = np.argmax(improvement_factors)
    improvement_factors = improvement_factors[:best_n] + [
        improvement_factors[best_n]
    ] * (len(improvement_factors) - best_n)

    ax_left.plot(ns(d), improvement_factors, label=f"$s = 10^{j}$")

ax_left.set_xscale("log")
ax_left.set_xlabel(r"Number of qubits $n$")
ax_left.set_ylabel("Toffoli cost improvement")
ax_left.set_xlim(6, 5 * 10**3)
ax_left.set_ylim(2, 14)
ax_left.legend(loc="lower right", reverse=True)
ax_left.grid(which="major", axis="y")
ax_left.grid(which="major", axis="x")
ax_left.grid(which="minor", axis="x")

# Right plot

for j, quotient in toffoli_quotients_unrest.items():
    d = 10**j
    ax_right.plot(ns_selected(d), quotient, label=f"$s = 10^{j}$")

ax_right.set_xscale("log")
ax_right.set_xlabel(r"Number of qubits $n$")
ax_right.set_ylabel(r"\#Toffolis/$s$")
ax_right.set_ylim(0.8, 3.2)
ax_right.set_xlim(8, 520)
ax_right.grid(which="major", axis="y")
ax_right.grid(which="major", axis="x")
ax_right.grid(which="minor", axis="x")

ax_right.set_title("Random states (numerical)", fontsize=9)
ax_left.set_title("Worst case (analytical)", fontsize=9)

fig.savefig("figure_2.pdf", bbox_inches="tight")

# Create figure 10

import matplotlib.pyplot as plt

formatter = rsmf.setup(
    r"\documentclass[twocolumn, a4paper, unpublished]{quantumarticle}"  # only want one column figure
)
fig = formatter.figure()

unrest_colors = []
for j, quotient in toffoli_quotients_unrest.items():
    d = 10**j
    line = plt.plot(ns_selected(d), quotient, label=f"$s = 10^{j}$")[0]
    unrest_colors.append(line.get_color())

for (j, quotient), col in zip(toffoli_quotients_rest.items(), unrest_colors):
    d = 10**j
    plt.plot(ns_selected(d), quotient, linestyle="dashed", color=col)

plt.title("Random states", fontsize=10)
plt.xscale("log")
plt.xlabel("Number of qubits $n$")
plt.ylabel(r"\#Toffolis/s")
plt.ylim(0.8, 3.2)
plt.xlim(8, 520)
plt.grid(which="major", axis="y")
plt.grid(which="major", axis="x")
plt.grid(which="minor", axis="x")
plt.legend(loc="upper right", reverse=True)

plt.savefig("figure_10.pdf", bbox_inches="tight")
