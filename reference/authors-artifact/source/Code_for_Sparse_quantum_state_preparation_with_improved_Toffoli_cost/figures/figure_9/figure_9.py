# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

from sparse_state_preparation import (
    random_tableau,
    SparseStatePreparation,
    fast_toffoli_counter,
)

from qualtran import QFxp
from qualtran.resource_counting import QECGatesCost, get_cost_value, QubitCount

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import rsmf

import numpy as np

# Plot the two graphs of Figure 9

# Get the states and coefficients
n = 80  # number of qubits
s = 10000  # number of non-zero basis states

seed = 8769876986

rng = np.random.default_rng(seed)
states = random_tableau(s, n, seed=seed)

real_ = rng.normal(loc=0.0, scale=1.0, size=s)
imag_ = rng.normal(loc=0.0, scale=1.0, size=s)
complex_ = imag_ + 1.0j * imag_

coeffs_real = real_ / np.linalg.norm(real_)  # for purely real state
coeffs_general = complex_ / np.linalg.norm(complex_)  # for generic state


def toffoli_cost(cost):
    """
    Count the Toffoli gates.
    """
    return cost.and_bloq + cost.cswap


isometry_modes = ["unrestricted", "restricted"]
coeff_labels = ["complex", "real"]

# Collect Toffoli and qubit costs of the different variants of isometry_mode:
# All combinations of complex/purely real coefficients and restricted and unrestricted version of
# the isometry algorithm.

emtpy_counts = lambda: {
    label: {mode: {} for mode in isometry_modes} for label in coeff_labels
}
isometry_costs = emtpy_counts()
uncompute_costs = emtpy_counts()
phase_prep_costs = emtpy_counts()
amplitude_prep_costs = emtpy_counts()
qubit_counts = emtpy_counts()

max_k_vals = list(range(6))  # Set after inspection.

for restricted, mode in zip([False, True], isometry_modes):
    prep = SparseStatePreparation(
        states, coeffs_general, QFxp(15, 15), 0, restricted, False
    )  # max_k and coeffs are irrelevant for the isometry itself

    iso_cost = fast_toffoli_counter(prep.isometry.circuit)
    iso_qubits = n + prep.isometry.subspace_bitsize + (1 if restricted else -1)

    for coeff, coeff_label in zip([coeffs_general, coeffs_real], coeff_labels):
        for max_k in max_k_vals:
            phases_in_isometry = restricted and (coeff_label == "real")

            prep = SparseStatePreparation(
                states, coeff, QFxp(15, 15), max_k, restricted, phases_in_isometry
            )

            # Get Toffoli and qubit costs.
            dense_cost = toffoli_cost(
                get_cost_value(prep.dense_state_prep, QECGatesCost())
            )
            dense_cost_amplitudes = toffoli_cost(
                get_cost_value(
                    prep.dense_state_prep.prepare_amplitudes_bloq(), QECGatesCost()
                )
            )
            dense_qubits = get_cost_value(prep.dense_state_prep, QubitCount())

            if phases_in_isometry:
                dense_cost_phases = 0
            else:
                dense_cost_phases = toffoli_cost(
                    get_cost_value(
                        prep.dense_state_prep.prepare_phases_bloq(), QECGatesCost()
                    )
                )

            if restricted:
                dense_cost_uncompute = 0
            else:
                dense_cost_uncompute = toffoli_cost(
                    get_cost_value(
                        prep.dense_state_prep.uncompute_bloq(), QECGatesCost()
                    )
                )

            assert (
                dense_cost
                == dense_cost_amplitudes + dense_cost_uncompute + dense_cost_phases
            )

            # Store the costs.
            uncompute_costs[coeff_label][mode][max_k] = dense_cost_uncompute
            phase_prep_costs[coeff_label][mode][max_k] = dense_cost_phases
            amplitude_prep_costs[coeff_label][mode][max_k] = dense_cost_amplitudes

            qubit_counts[coeff_label][mode][max_k] = max(iso_qubits, dense_qubits)
            isometry_costs[coeff_label][mode][max_k] = iso_cost

# Reorder for barplots.
iso_matrix = {
    label: np.array(
        [[c[mode][k_max] for k_max in max_k_vals] for mode in isometry_modes]
    )
    for label, c in isometry_costs.items()
}
dense_uncompute_matrix = {
    label: np.array(
        [[c[mode][k_max] for k_max in max_k_vals] for mode in isometry_modes]
    )
    for label, c in uncompute_costs.items()
}
dense_amplitude_matrix = {
    label: np.array(
        [[c[mode][k_max] for k_max in max_k_vals] for mode in isometry_modes]
    )
    for label, c in amplitude_prep_costs.items()
}
dense_phase_matrix = {
    label: np.array(
        [[c[mode][k_max] for k_max in max_k_vals] for mode in isometry_modes]
    )
    for label, c in phase_prep_costs.items()
}

qubit_matrix = {
    label: np.array(
        [[c[mode][k_max] for k_max in max_k_vals] for mode in isometry_modes]
    )
    for label, c in qubit_counts.items()
}

# Plot figure 9
formatter = rsmf.setup(
    r"\documentclass[onecolumn, a4paper, unpublished]{quantumarticle}"
)
fig = formatter.figure(aspect_ratio=0.45)

gs = gridspec.GridSpec(
    2, 2, height_ratios=[2, 1], hspace=0.02, width_ratios=[1, 1], wspace=0.02
)

ax_cost = [fig.add_subplot(gs[0, 0])]
ax_cost.append(fig.add_subplot(gs[0, 1], sharey=ax_cost[0]))
ax_qubits = [fig.add_subplot(gs[1, 0], sharex=ax_cost[0])]
ax_qubits.append(fig.add_subplot(gs[1, 1], sharey=ax_qubits[0], sharex=ax_cost[1]))

bar_width = 0.35
indices = np.arange(len(max_k_vals))

iso_colors = ["tab:blue", "tab:cyan"]
amplitudes_color = "darkorange"
phases_color = "tab:green"
uncompute_color = "tab:purple"

labels = ["isometry (unrestricted)", "isometry (restricted)"]

legend_handles_iso = []

for j, complex in enumerate(coeff_labels):
    for i, (mode, label, iso_color) in enumerate(
        zip(isometry_modes, labels, iso_colors)
    ):
        h_iso = ax_cost[j].bar(
            indices + i * bar_width,
            iso_matrix[complex][i],
            width=bar_width,
            edgecolor="black",
            linewidth=0.008,
            color=iso_color,
            hatch="///",
            hatch_linewidth=0.01,
        )
        legend_handles_iso.append(h_iso)
        h_amplitude = ax_cost[j].bar(
            indices + i * bar_width,
            dense_amplitude_matrix[complex][i],
            width=bar_width,
            edgecolor="black",
            linewidth=0.008,
            bottom=iso_matrix[complex][i],
            color=amplitudes_color,
        )
        h_phase = ax_cost[j].bar(
            indices + i * bar_width,
            dense_phase_matrix[complex][i],
            width=bar_width,
            edgecolor="black",
            linewidth=0.008,
            bottom=dense_amplitude_matrix[complex][i] + iso_matrix[complex][i],
            color=phases_color,
        )
        h_uncompute = ax_cost[j].bar(
            indices + i * bar_width,
            dense_uncompute_matrix[complex][i],
            width=bar_width,
            bottom=dense_amplitude_matrix[complex][i]
            + iso_matrix[complex][i]
            + dense_phase_matrix[complex][i],
            color=uncompute_color,
            edgecolor="black",
            linewidth=0.008,
        )

    ax_cost[0].set_ylabel(r"Toffoli count")
    ax_cost[1].tick_params(labelleft=False)
    ax_cost[j].set_xticks([])
    ax_cost[j].set_xticklabels([])

    for i, (mode, iso_color) in enumerate(zip(isometry_modes, iso_colors)):
        ax_qubits[j].bar(
            indices + i * bar_width,
            qubit_matrix[complex][i],
            width=bar_width,
            edgecolor="black",
            color="gray",
            linewidth=0.01,
        )

    ax_qubits[1].tick_params(labelleft=False)
    ax_qubits[0].set_ylabel("Qubit count")
    ax_qubits[j].grid(axis="y", linestyle="--", alpha=0.6)

    ax_qubits[j].set_xlabel(r"$r_{max}$")
    xtick_labels = [str(k) for k in max_k_vals]
    ax_qubits[j].set_xticks(indices + bar_width / 2)
    ax_qubits[j].set_xticklabels(xtick_labels)

    legend_handles = legend_handles_iso[:2]
    legend_labels = ["isometry (unrest.)", "isometry (restr.)"]
    ax_cost[0].legend(
        legend_handles, legend_labels, ncol=1, loc="upper right", framealpha=0.9
    )

    legend_handles = [h_uncompute, h_phase, h_amplitude]
    legend_labels = ["uncompute", "phases", "amplitudes"]
    ax_cost[1].legend(
        legend_handles, legend_labels, ncol=1, loc="upper right", framealpha=0.9
    )

    ax_cost[j].grid(axis="y", linestyle="--", alpha=0.6)

ax_cost[1].set_title("Random purely real state", fontsize=10)
ax_cost[0].set_title("Random generic state", fontsize=10)

plt.savefig("figure_9.pdf", bbox_inches="tight")
