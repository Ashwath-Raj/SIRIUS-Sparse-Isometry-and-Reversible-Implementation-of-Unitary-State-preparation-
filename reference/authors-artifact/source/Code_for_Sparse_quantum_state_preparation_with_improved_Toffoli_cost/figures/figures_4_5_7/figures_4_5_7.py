# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0


import numpy as np

from qualtran import BloqBuilder, Register, QBit, Side
from qualtran.drawing import (
    get_musical_score_data,
    draw_musical_score,
    ClassicalSimGraphDrawer,
)

from sparse_state_preparation import IsometryToSubspaceViaBatching

# Get the circuits for Figure 4 and the PUIs in Figure 7, together with information
# to create Figure 5

tableau = np.array(
    [
        [0, 1, 1, 1, 0, 1, 1],
        [1, 1, 1, 0, 1, 1, 1],
        [1, 0, 0, 1, 0, 1, 0],
        [0, 1, 1, 0, 1, 1, 0],
        [1, 0, 1, 1, 1, 0, 1],
        [1, 0, 0, 1, 1, 1, 1],
        [1, 1, 1, 1, 0, 1, 0],
    ],
)

# Run our isometry algorithm on the tableau above.
bb = BloqBuilder()
full = bb.add_register(Register("full", QBit(), shape=(7,), side=Side.LEFT))
full = bb.join(full)

isometry = IsometryToSubspaceViaBatching(tableau.astype(np.bool))

subspace = bb.add(isometry, full=full)
subspace = bb.split(subspace)

bloq = bb.finalize(subspace=subspace)

# Visualize different parts of the circuit using musical scores.

msd = get_musical_score_data(isometry.decompose_bloq().flatten_once().flatten_once())
fig, ax = draw_musical_score(msd, max_width=1000, max_height=1000)
fig.savefig("figure_4_musical_score.pdf")  # Can nicely see the row creation -> Figure 4

msd = get_musical_score_data(isometry.decompose_bloq().flatten_once())
fig, ax = draw_musical_score(msd, max_width=1000, max_height=1000)
fig.savefig("figure_7_musical_score.pdf")  # Can nicely see the PUIs -> Figure 7

# Print the input and output states.

print("In\n", tableau)
print("Out")
for row in tableau:
    print(bloq.call_classically(full=tuple(row))[0])

# Get information for Figure 5:
#
# The interesting part is the second group of PrepareRow bloqs.
# The states in Figure 5 are the states after the first PrepareRow bloq in this second group.
for row in tableau[[3, 4, 6]]:
    drawer = ClassicalSimGraphDrawer(
        bloq.flatten_once().flatten_once(), vals={"full": tuple(row)}
    )

    with open(
        "figure_5_" + "".join(str(x) for x in row) + ".svg", "w", encoding="utf-8"
    ) as f:
        f.write(drawer.get_svg().data)
