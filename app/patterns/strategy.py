from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RiskAssessment:
    risk_level: str
    risk_score: float
    risk_factors: list[str]
    summary: str
    advice: str = ""


@dataclass
class InterventionSuggestion:
    intervention_type: str
    recommendation: str
    reasoning: str
    priority: str


class AIStrategy(ABC):
    """Abstract strategy — defines what any AI engine must be able to do."""

    @abstractmethod
    def analyze_risk(self, student_data: dict) -> RiskAssessment:
        pass

    @abstractmethod
    def suggest_intervention(self, risk_data: dict) -> InterventionSuggestion:
        pass

    @abstractmethod
    def explain_reasoning(self, analysis: dict) -> str:
        pass


class RiskAnalysisContext:
    """Context that holds the current AI strategy.
    Swap strategies at runtime without changing any calling code.
    """

    def __init__(self, strategy: AIStrategy):
        self._strategy = strategy

    @property
    def strategy_name(self) -> str:
        return self._strategy.__class__.__name__

    def set_strategy(self, strategy: AIStrategy):
        self._strategy = strategy

    def analyze(self, student_data: dict) -> RiskAssessment:
        return self._strategy.analyze_risk(student_data)

    def suggest(self, risk_data: dict) -> InterventionSuggestion:
        return self._strategy.suggest_intervention(risk_data)

    def explain(self, analysis: dict) -> str:
        return self._strategy.explain_reasoning(analysis)
