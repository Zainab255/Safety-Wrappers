"""
Base wrapper: finite-state monitor interface.
Each wrapper defines: State, Observed events, Actions (ALLOW / BLOCK / MODIFY / REQUERY).
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, List, Tuple


class Action(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    MODIFY = "MODIFY"
    REQUERY = "REQUERY"


class BaseWrapper(ABC):
    """Finite-state monitor: explicit internal state, observable events, actions."""

    name: str = "base"
    config: dict = {}

    def __init__(self, config: dict):
        self.config = config or {}

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state for a new run."""
        pass

    @abstractmethod
    def step(
        self,
        user_prompt: str,
        model_output: str,
        call_index: int,
    ) -> Tuple[Action, str]:
        """
        Observe: user_prompt, model_output, call_index.
        Returns (action, output_to_use).
        - ALLOW: use model_output as final
        - BLOCK: do not use; return block message
        - MODIFY: use modified output
        - REQUERY: request another model call (if budget allows)
        """
        pass

    def get_state(self) -> dict:
        """Explicit internal state for trace logging."""
        return {}
