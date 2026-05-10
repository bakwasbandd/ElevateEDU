from app.ai.mock_ai import MockAIStrategy
from app.ai.cloud_llm import CloudLLMStrategy
from app.ai.local_llm import LocalLLMStrategy
from app.patterns.strategy import AIStrategy

_STRATEGY_MAP = {
    "mock": MockAIStrategy,
    "cloud": CloudLLMStrategy,
    "local": LocalLLMStrategy,
}


def get_strategy(name: str = "mock") -> AIStrategy:
    """Get an AI strategy instance by name. Defaults to mock if unknown."""
    cls = _STRATEGY_MAP.get(name, MockAIStrategy)
    return cls()
