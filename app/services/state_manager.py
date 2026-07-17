"""連続判定による状態確定を管理する。

1回の判定だけで表示状態を変えず、同じ判定がN回（設定可能）連続した
場合にのみ確定状態を更新する。状態はプロセスのメモリ上に保持する
（再起動時はリセットされる想定のシンプルな実装）。
"""

from __future__ import annotations

import logging
import threading

from app.models import DetectionStatus, SpaceState

logger = logging.getLogger(__name__)


class StateManager:
    def __init__(self, required_consecutive_results: int) -> None:
        self.required_consecutive_results = max(1, required_consecutive_results)
        self._states: dict[int, SpaceState] = {}
        self._lock = threading.Lock()

    def get_state(self, space_id: int) -> SpaceState:
        with self._lock:
            return self._get_or_create(space_id)

    def _get_or_create(self, space_id: int) -> SpaceState:
        state = self._states.get(space_id)
        if state is None:
            state = SpaceState(space_id=space_id, confirmed_status="unknown")
            self._states[space_id] = state
        return state

    def update(self, space_id: int, new_status: DetectionStatus) -> SpaceState:
        """1回分の判定結果を反映し、連続判定ルールを適用した状態を返す。"""
        with self._lock:
            state = self._get_or_create(space_id)

            if new_status == state.pending_status:
                state.pending_count += 1
            else:
                state.pending_status = new_status
                state.pending_count = 1

            if state.pending_count >= self.required_consecutive_results:
                if state.confirmed_status != new_status:
                    logger.info(
                        "space %s confirmed status changed: %s -> %s",
                        space_id,
                        state.confirmed_status,
                        new_status,
                    )
                state.confirmed_status = new_status

            return state

    def all_states(self) -> dict[int, SpaceState]:
        with self._lock:
            return dict(self._states)

    def remove_space(self, space_id: int) -> None:
        with self._lock:
            self._states.pop(space_id, None)

    def reset(self) -> None:
        with self._lock:
            self._states.clear()
