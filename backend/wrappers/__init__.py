from backend.wrappers.base import BaseWrapper, Action
from backend.wrappers.noop import NoopWrapper
from backend.wrappers.keyword import KeywordWrapper
from backend.wrappers.history import HistoryWrapper
from backend.wrappers.query_budget import QueryBudgetWrapper

WRAPPERS = {
    "noop": NoopWrapper,
    "keyword": KeywordWrapper,
    "history": HistoryWrapper,
    "query_budget": QueryBudgetWrapper,
}


def get_wrapper(name: str, config: dict) -> BaseWrapper:
    cls = WRAPPERS.get(name)
    if not cls:
        raise ValueError(f"Unknown wrapper: {name}")
    return cls(config)
