"""
No-op wrapper: baseline. Always ALLOW, no state.
"""

from backend.wrappers.base import BaseWrapper, Action


class NoopWrapper(BaseWrapper):
    """
    State: none (stateless).
    Observed events: user_prompt, model_output, call_index.
    Actions: always ALLOW.
    """

    name = "noop"

    def reset(self) -> None:
        pass

    def step(
        self,
        user_prompt: str,
        model_output: str,
        call_index: int,
    ) -> tuple:
        return Action.ALLOW, model_output

    def get_state(self) -> dict:
        return {"type": "stateless"}
