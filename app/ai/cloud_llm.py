import json
import httpx
from app.patterns.strategy import AIStrategy, RiskAssessment, InterventionSuggestion
from app.config import config
from app.ai.mock_ai import MockAIStrategy


class CloudLLMStrategy(AIStrategy):
    """Calls a cloud LLM API (Groq by default) for risk analysis.
    Swap providers by changing the config.
    """

    def __init__(self):
        self.api_key = (config.CLOUD_LLM_API_KEY or "").strip()
        self.model = (config.CLOUD_LLM_MODEL or "").strip()
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

    def _call_groq(self, prompt: str) -> str:
        """Make a request to the Groq API."""
        if not self.api_key:
            return "LLM call failed: GROQ_API_KEY is not set."
        if not self.model:
            return "LLM call failed: GROQ_MODEL is not set."

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an academic risk analysis assistant. Return JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        try:
            resp = httpx.post(
                url,
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            if resp.status_code == 429:
                return "LLM call failed: Rate limit exceeded (429 Too Many Requests). Please wait a minute before trying again."
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"LLM call failed: {str(e)}"

    def analyze_risk(self, student_data: dict) -> RiskAssessment:
        prompt = f"""You are an academic risk analysis AI. Analyze this student's data and respond in JSON only.

Student Data:
- Name: {student_data.get('name')}
- Attendance: {student_data.get('attendance_percentage', 100):.1f}%
- GPA: {student_data.get('gpa', 4.0):.2f}
- Late Submissions: {student_data.get('late_submission_percentage', 0):.1f}%
- Courses: {student_data.get('courses', [])}

Respond with this exact JSON structure:
{{"risk_level": "none|low|medium|high|critical", "risk_score": 0-100, "risk_factors": ["factor1", "factor2"], "summary": "brief summary", "advice": "actionable improvement plan"}}"""

        raw = self._call_groq(prompt)
        if raw.startswith("LLM call failed:"):
            fallback = self._fallback.analyze_risk(student_data)
            fallback.risk_factors = [raw, "Cloud LLM unavailable; using fallback analysis."] + fallback.risk_factors
            return self._apply_hard_rules(student_data, fallback)

        try:
            # try to extract JSON from the response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end])
            assessment = RiskAssessment(
                risk_level=parsed.get("risk_level", "medium"),
                risk_score=float(parsed.get("risk_score", 0.0)),
                risk_factors=parsed.get("risk_factors", []),
                summary=parsed.get("summary", raw),
                advice=parsed.get("advice", "No specific advice generated."),
            )
            return self._apply_hard_rules(student_data, assessment)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            assessment = RiskAssessment(
                risk_level="none", risk_score=0.0,
                risk_factors=[f"Could not parse LLM response: {str(e)}"],
                summary=raw[:500] if isinstance(raw, str) else "Request Failed",
                advice="Analysis failed. Please check Cloud LLM connection.",
            )
            return self._apply_hard_rules(student_data, assessment)

    def suggest_intervention(self, risk_data: dict) -> InterventionSuggestion:
        prompt = f"""You are an academic intervention advisor. Based on the risk data below, suggest a targeted intervention.

Risk Data:
- Type: {risk_data.get('primary_risk_type', 'academic')}
- Severity: {risk_data.get('severity', 'medium')}
- Risk Factors: {risk_data.get('risk_factors', [])}
- Student: {risk_data.get('student_name', 'Unknown')}

Respond with this exact JSON structure:
{{"intervention_type": "attendance|academic|submission", "recommendation": "detailed recommendation", "reasoning": "why this intervention", "priority": "low|medium|high|critical"}}"""

        raw = self._call_groq(prompt)
        if raw.startswith("LLM call failed:"):
            return self._fallback.suggest_intervention(risk_data)

        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end])
            return InterventionSuggestion(
                intervention_type=parsed.get("intervention_type", risk_data.get("primary_risk_type", "academic")),
                recommendation=parsed.get("recommendation", "Review student profile"),
                reasoning=parsed.get("reasoning", "Based on risk analysis"),
                priority=parsed.get("priority", "medium"),
            )
        except (json.JSONDecodeError, ValueError):
            return InterventionSuggestion(
                intervention_type=risk_data.get("primary_risk_type", "academic"),
                recommendation=raw[:500],
                reasoning="Generated by Cloud LLM",
                priority="medium",
            )

    def explain_reasoning(self, analysis: dict) -> str:
        prompt = f"""Explain in plain English why this student is at risk, in 2-3 sentences.

Analysis:
- Risk Level: {analysis.get('risk_level', 'unknown')}
- Risk Score: {analysis.get('risk_score', 0)}
- Factors: {analysis.get('risk_factors', [])}"""

        raw = self._call_groq(prompt)
        if raw.startswith("LLM call failed:"):
            return self._fallback.explain_reasoning(analysis)
        return raw
