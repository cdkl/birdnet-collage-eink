import pytest
import threading


class MockEvent:
    def __init__(self):
        self._set = False

    def set(self):
        self._set = True

    def wait(self, timeout=None):
        return self._set

    def clear(self):
        self._set = False

    def is_set(self):
        return self._set


def make_state():
    return {
        "wake_event": MockEvent(),
        "force_refresh_once": False,
        "clear_requested": False,
        "saturation": 0.5,
    }


def test_button_a_force_refresh():
    from src.buttons import ButtonMonitor
    state = make_state()
    bm = ButtonMonitor(state)

    bm._handle("A")

    assert state["force_refresh_once"] is True
    assert state["wake_event"].is_set() is True
    assert state["clear_requested"] is False


def test_button_b_decrement_saturation():
    from src.buttons import ButtonMonitor
    state = make_state()
    state["saturation"] = 0.6
    bm = ButtonMonitor(state)

    bm._handle("B")

    assert state["saturation"] == 0.5
    assert state["force_refresh_once"] is True
    assert state["wake_event"].is_set() is True


def test_button_b_clamps_at_minimum():
    from src.buttons import ButtonMonitor
    state = make_state()
    state["saturation"] = 0.2
    bm = ButtonMonitor(state)

    bm._handle("B")

    assert state["saturation"] == 0.2
    assert state["force_refresh_once"] is True


def test_button_c_increment_saturation():
    from src.buttons import ButtonMonitor
    state = make_state()
    state["saturation"] = 0.4
    bm = ButtonMonitor(state)

    bm._handle("C")

    assert state["saturation"] == 0.5
    assert state["force_refresh_once"] is True
    assert state["wake_event"].is_set() is True


def test_button_c_clamps_at_maximum():
    from src.buttons import ButtonMonitor
    state = make_state()
    state["saturation"] = 1.0
    bm = ButtonMonitor(state)

    bm._handle("C")

    assert state["saturation"] == 1.0
    assert state["force_refresh_once"] is True


def test_button_d_clear_and_force_refresh():
    from src.buttons import ButtonMonitor
    state = make_state()
    bm = ButtonMonitor(state)

    bm._handle("D")

    assert state["clear_requested"] is True
    assert state["force_refresh_once"] is True
    assert state["wake_event"].is_set() is True


def test_no_floating_point_drift():
    from src.buttons import ButtonMonitor
    state = make_state()
    state["saturation"] = 0.2
    bm = ButtonMonitor(state)

    for _ in range(8):
        bm._handle("C")

    assert state["saturation"] == 1.0

    for _ in range(8):
        bm._handle("B")

    assert state["saturation"] == 0.2