"""Optional GPU parity checks. These skip only when CuPy/CUDA is unavailable."""
import pytest
from sparseprep.gates import CMX, CX, MCX, NegativeControlToffoli, SWAP, Toffoli, X
from sparseprep.model import bitstring_to_int, int_to_bitstring
from sparseprep.simulator import simulate_support


def _cupy_available():
    try:
        import cupy as cp
        return cp.cuda.runtime.getDeviceCount() > 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _cupy_available(), reason="CuPy CUDA backend unavailable in this Python environment")


def test_cupy_matches_cpu_for_mixed_gate_sequence():
    from sparseprep.backends.cupy_simulator import simulate_int_states_cupy, cp_asnumpy
    states = ("00000", "10001", "01110", "11111")
    gates = (X(0), CX(0, 4), SWAP(1, 3), Toffoli(0, 1, 2),
             NegativeControlToffoli((0, 3), 4, (0, 1)), CMX(2, (0, 3)), MCX((0, 1), 4, (1, 0)))
    cpu = simulate_support(states, gates)
    gpu_ints = simulate_int_states_cupy([bitstring_to_int(s) for s in states], 5, gates)
    gpu = tuple(int_to_bitstring(int(x), 5) for x in cp_asnumpy(gpu_ints))
    assert gpu == cpu


def test_cupy_kernel_executes_on_device():
    import cupy as cp
    from sparseprep.backends.cupy_simulator import simulate_int_states_cupy
    result = simulate_int_states_cupy([0, 1, 2, 3], 3, (X(0), CX(0, 2)))
    cp.cuda.Stream.null.synchronize()
    assert cp.asnumpy(result).tolist() == [5, 4, 7, 6]
