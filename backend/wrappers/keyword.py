"""
Keyword-based wrapper: block if prompt contains banned keywords.
"""

from backend.wrappers.base import BaseWrapper, Action


class KeywordWrapper(BaseWrapper):
    """
    State: none (stateless; decision from current prompt only).
    Observed events: user_prompt, model_output, call_index.
    Actions: BLOCK if prompt contains banned keyword; else ALLOW.
    """

    name = "keyword"
    BLOCK_MESSAGE = "[Blocked by keyword wrapper]"

    def __init__(self, config: dict):
        super().__init__(config)
        self._keywords = [
            k.lower() for k in self.config.get("banned_keywords", [])
        ]

    def reset(self) -> None:
        pass

    def step(
        self,
        user_prompt: str,
        model_output: str,
        call_index: int,
    ) -> tuple:
        prompt_lower = user_prompt.lower()
        for kw in self._keywords:
            if kw in prompt_lower:
                return Action.BLOCK, self.BLOCK_MESSAGE
        return Action.ALLOW, model_output

    def get_state(self) -> dict:
        return {"banned_keywords": self._keywords}
