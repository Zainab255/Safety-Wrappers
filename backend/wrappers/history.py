"""
History-based wrapper: bounded history of length k.
REQUERY if model output is empty or duplicate of recent; else ALLOW.
"""

from backend.wrappers.base import BaseWrapper, Action


class HistoryWrapper(BaseWrapper):
    """
    State: buffer of last k model outputs (bounded history).
    Observed events: user_prompt, model_output, call_index.
    Actions: REQUERY if output empty or in history (up to budget); else ALLOW.
    """

    name = "history"

    def __init__(self, config: dict):
        super().__init__(config)
        self._k = int(self.config.get("k", 3))
        self._buffer: list = []

    def reset(self) -> None:
        self._buffer = []

    def step(
        self,
        user_prompt: str,
        model_output: str,
        call_index: int,
    ) -> tuple:
        out_stripped = (model_output or "").strip()
        if not out_stripped:
            return Action.REQUERY, ""
        if out_stripped in self._buffer:
            return Action.REQUERY, ""
        self._buffer.append(out_stripped)
        if len(self._buffer) > self._k:
            self._buffer.pop(0)
        return Action.ALLOW, model_output

    def get_state(self) -> dict:
        return {"k": self._k, "buffer": list(self._buffer)}
