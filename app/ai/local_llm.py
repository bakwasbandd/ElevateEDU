import json
import httpx
from app.patterns.strategy import AIStrategy, RiskAssessment, InterventionSuggestion
from app.config import config
from app.ai.mock_ai import MockAIStrategy


class LocalLLMStrategy(AIStrategy):
    """Calls a local LLM through Ollama's API.
    Same interface as CloudLLMStrategy — that's the whole point of Strategy pattern.
    """

    def __init__(self):
        self.base_url = config.LOCAL_LLM_URL
        self.model = config.LOCAL_LLM_MODEL
        self._fallback = MockAIStrategy()

    def _apply_hard_rules(self, student_data: dict, assessment: RiskAssessment) -> RiskAssessment:
        if student_data.get("gpa", 4.0) < 1.25:
            factors = list(assessment.risk_factors)
            factors.insert(0, f"GPA of {student_data.get('gpa', 4.0):.2f} is below the 1.25 critical threshold")
            return RiskAssessment(
                risk_level="critical",
                risk_score=max(assessment.risk_score, 80.0),
                risk_factors=factors,
                summary=assessment.summary,
                advice=assessment.advice,
            )
        return assessment

    def _call_ollama(self, prompt: str) -> str:
        """Hit the Ollama generate endpoint."""
        try:
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False, "format": "json"},
                timeout=180.0,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            return f"LLM call failed: {str(e)}"

    def analyze_risk(self, student_data: dict) -> RiskAssessment:
        prompt = f"""You are an academic risk analysis AI. Analyze this student and return JSON only.

Student: {student_data.get('name')}
Attendance: {student_data.get('attendance_percentage', 100):.1f}%
GPA: {student_data.get('gpa', 4.0):.2f}
Late Submissions: {student_data.get('late_submission_percentage', 0):.1f}%

Return JSON: {{"risk_level": "none|low|medium|high|critical", "risk_score": 0-100, "risk_factors": ["..."], "summary": "...", "advice": "..."}}"""

        raw = self._call_ollama(prompt)
        if raw.startswith("LLM call failed:"):
            fallback = self._fallback.analyze_risk(student_data)
            fallback.risk_factors = [raw, "Local LLM unavailable; using fallback analysis."] + fallback.risk_factors
            return self._apply_hard_rules(student_data, fallback)
        if not raw:
            fallback = self._fallback.analyze_risk(student_data)
            fallback.risk_factors = ["Local LLM unavailable; using fallback analysis."] + fallback.risk_factors
            return self._apply_hard_rules(student_data, fallback)
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end])
            return self._apply_hard_rules(student_data, RiskAssessment(
                risk_level=parsed.get("risk_level", "medium"),
                risk_score=float(parsed.get("risk_score", 50)),
                risk_factors=parsed.get("risk_factors", []),
                summary=parsed.get("summary", raw),
                advice=parsed.get("advice", "No specific advice generated."),
            ))
        except (json.JSONDecodeError, ValueError):
            fallback = self._fallback.analyze_risk(student_data)
            fallback.risk_factors = ["Local LLM returned an unreadable response; using fallback analysis."] + fallback.risk_factors
            return self._apply_hard_rules(student_data, fallback)

    def suggest_intervention(self, risk_data: dict) -> InterventionSuggestion:
        prompt = f"""Suggest an academic intervention for a student with these risks:
Type: {risk_data.get('primary_risk_type', 'academic')}
Severity: {risk_data.get('severity', 'medium')}
Factors: {risk_data.get('risk_factors', [])}

Return JSON: {{"intervention_type": "...", "recommendation": "...", "reasoning": "...", "priority": "..."}}"""

        raw = self._call_ollama(prompt)
        if raw.startswith("LLM call failed:"):
            return self._fallback.suggest_intervention(risk_data)
        if not raw:
            return self._fallback.suggest_intervention(risk_data)
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end])
            return InterventionSuggestion(
                intervention_type=parsed.get("intervention_type", "academic"),
                recommendation=parsed.get("recommendation", "Review student profile"),
                reasoning=parsed.get("reasoning", "Based on local analysis"),
                priority=parsed.get("priority", "medium"),
            )
        except (json.JSONDecodeError, ValueError):
            return self._fallback.suggest_intervention(risk_data)

    def explain_reasoning(self, analysis: dict) -> str:
        prompt = f"""Briefly explain why this student is at academic risk:
Risk Level: {analysis.get('risk_level')}
Score: {analysis.get('risk_score')}
Factors: {analysis.get('risk_factors', [])}

Keep it to 2-3 sentences."""

        raw = self._call_ollama(prompt)
        if raw:
            if raw.startswith("LLM call failed:"):
                return self._fallback.explain_reasoning(analysis)
            return raw
        return self._fallback.explain_reasoning(analysis)
