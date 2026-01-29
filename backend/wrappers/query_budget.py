"""
Query-budget wrapper: max N model calls (re-queries).
After N calls, force ALLOW or BLOCK on last output.
"""

from backend.wrappers.base import BaseWrapper, Action


class QueryBudgetWrapper(BaseWrapper):
    """
    State: call_count (number of model invocations so far).
    Observed events: user_prompt, model_output, call_index.
    Actions: if call_index >= max_queries, ALLOW last output; else may REQUERY.
    This wrapper only enforces budget; it does not trigger REQUERY itself.
    Typically composed or used with another wrapper that may REQUERY.
    Here we implement: allow up to N calls, then ALLOW final output.
    """

    name = "query_budget"

    def __init__(self, config: dict):
        super().__init__(config)
        self._max_queries = int(self.config.get("max_queries", 2))
        self._calls = 0

    def reset(self) -> None:
        self._calls = 0

    def step(
        self,
        user_prompt: str,
        model_output: str,
        call_index: int,
    ) -> tuple:
        self._calls = call_index + 1
        # Cap at max_queries total calls; always ALLOW (orchestrator enforces cap).
        return Action.ALLOW, model_output

    def get_state(self) -> dict:
        return {"call_count": self._calls, "max_queries": self._max_queries}
