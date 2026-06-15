"""The eval runner passes the gate on the current golden set."""
from eval_runner.runner import run


def test_eval_gate_passes():
    assert run(gate=True) == 0
