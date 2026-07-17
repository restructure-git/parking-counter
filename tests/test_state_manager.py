from __future__ import annotations

from app.services.state_manager import StateManager


def test_initial_state_is_unknown() -> None:
    manager = StateManager(required_consecutive_results=3)

    state = manager.get_state(1)

    assert state.confirmed_status == "unknown"
    assert state.pending_status is None
    assert state.pending_count == 0


def test_confirms_after_three_consecutive_results() -> None:
    manager = StateManager(required_consecutive_results=3)

    state1 = manager.update(1, "occupied")
    assert state1.confirmed_status == "unknown"
    assert state1.pending_count == 1

    state2 = manager.update(1, "occupied")
    assert state2.confirmed_status == "unknown"
    assert state2.pending_count == 2

    state3 = manager.update(1, "occupied")
    assert state3.confirmed_status == "occupied"
    assert state3.pending_count == 3


def test_different_result_resets_pending_count() -> None:
    manager = StateManager(required_consecutive_results=3)

    manager.update(1, "occupied")
    manager.update(1, "occupied")
    state = manager.update(1, "empty")

    assert state.pending_status == "empty"
    assert state.pending_count == 1
    assert state.confirmed_status == "unknown"  # まだ確定していない


def test_confirmed_status_persists_until_new_confirmation() -> None:
    manager = StateManager(required_consecutive_results=3)

    for _ in range(3):
        manager.update(1, "occupied")
    # 一度だけ違う結果が来ても、確定状態はすぐには変わらない
    state = manager.update(1, "empty")

    assert state.confirmed_status == "occupied"
    assert state.pending_status == "empty"
    assert state.pending_count == 1


def test_unknown_requires_three_consecutive_to_confirm() -> None:
    manager = StateManager(required_consecutive_results=3)

    for _ in range(3):
        manager.update(1, "occupied")

    manager.update(1, "unknown")
    state = manager.update(1, "unknown")
    assert state.confirmed_status == "occupied"  # まだ2回目、確定は維持

    state = manager.update(1, "unknown")
    assert state.confirmed_status == "unknown"  # 3回連続でunknownが確定


def test_states_are_independent_per_space() -> None:
    manager = StateManager(required_consecutive_results=3)

    for _ in range(3):
        manager.update(1, "occupied")
    for _ in range(3):
        manager.update(2, "empty")

    assert manager.get_state(1).confirmed_status == "occupied"
    assert manager.get_state(2).confirmed_status == "empty"


def test_reset_clears_all_states() -> None:
    manager = StateManager(required_consecutive_results=3)
    for _ in range(3):
        manager.update(1, "occupied")

    manager.reset()

    assert manager.get_state(1).confirmed_status == "unknown"
