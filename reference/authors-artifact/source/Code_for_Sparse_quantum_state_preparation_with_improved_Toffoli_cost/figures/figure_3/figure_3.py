# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from qualtran import BloqBuilder, Register, QBit
from qualtran.bloqs.mcmt import MultiControlX
from qualtran.drawing import get_musical_score_data, draw_musical_score

from sparse_state_preparation import MultiTargetCNOTShaped

tableau = np.array(
    [
        [0, 1, 1, 1, 0, 1, 1],
        [1, 1, 1, 0, 1, 1, 1],
        [1, 0, 0, 1, 0, 1, 0],
        [0, 1, 1, 0, 1, 1, 0],
        [1, 0, 1, 1, 1, 0, 1],
        [1, 0, 0, 1, 1, 1, 1],
        [1, 1, 1, 1, 0, 1, 0],
    ]
)

# Apply the algorithm of Malvetti et. al [https://quantum-journal.org/papers/q-2021-03-15-412/] by hand.

bb = BloqBuilder()
state = bb.add_register(Register("state", QBit(), shape=(7,)))

state[3], state[[5, 6]] = bb.add(
    MultiTargetCNOTShaped(2), control=state[3], targets=state[[5, 6]]
)
state[[0, 1, 2]], state[3] = bb.add(
    MultiControlX((0, 1, 1)), controls=state[[0, 1, 2]], target=state[3]
)

state[4], state[[5, 6]] = bb.add(
    MultiTargetCNOTShaped(2), control=state[4], targets=state[[5, 6]]
)
state[[0, 1, 2]], state[4] = bb.add(
    MultiControlX((1, 1, 1)), controls=state[[0, 1, 2]], target=state[4]
)

state[3], state[[6]] = bb.add(
    MultiTargetCNOTShaped(1), control=state[3], targets=state[[6]]
)
state[[0, 1, 2]], state[3] = bb.add(
    MultiControlX((1, 0, 0)), controls=state[[0, 1, 2]], target=state[3]
)

state[3], state[[2, 4]] = bb.add(
    MultiTargetCNOTShaped(2), control=state[3], targets=state[[2, 4]]
)
state[[0, 1, 2]], state[3] = bb.add(
    MultiControlX((0, 1, 0)), controls=state[[0, 1, 2]], target=state[3]
)

state[3], state[[2]] = bb.add(
    MultiTargetCNOTShaped(1), control=state[3], targets=state[[2]]
)
state[[0, 1, 2]], state[3] = bb.add(
    MultiControlX((1, 0, 1)), controls=state[[0, 1, 2]], target=state[3]
)

state[4], state[[1, 5]] = bb.add(
    MultiTargetCNOTShaped(2), control=state[4], targets=state[[1, 5]]
)
state[[0, 1, 2]], state[4] = bb.add(
    MultiControlX((1, 1, 0)), controls=state[[0, 1, 2]], target=state[4]
)

state[3], state[[0, 1, 2]] = bb.add(
    MultiTargetCNOTShaped(3), control=state[3], targets=state[[0, 1, 2]]
)
state[[0, 1, 2]], state[3] = bb.add(
    MultiControlX((0, 0, 0)), controls=state[[0, 1, 2]], target=state[3]
)

bloq = bb.finalize(state=state)

# Visualize the circuit using a musical score.
msd = get_musical_score_data(bloq)
fig, ax = draw_musical_score(msd, max_width=1000, max_height=1000)
fig.savefig("figure_3_musical_score.pdf")

# Print the input and output states.
print("In\n", tableau)
print("Out")
for row in tableau:
    print(bloq.call_classically(state=tuple(row))[0])
