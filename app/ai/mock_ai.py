from app.patterns.strategy import AIStrategy, RiskAssessment, InterventionSuggestion


class MockAIStrategy(AIStrategy):
    """Rule-based AI that works without any LLM.
    Good for testing, demos, and when no API key is available.
    """

    def analyze_risk(self, student_data: dict) -> RiskAssessment:
        risk_factors = []
        score = 0.0

        attendance = student_data.get("attendance_percentage", 100)
        gpa = student_data.get("gpa", 4.0)
        late_pct = student_data.get("late_submission_percentage", 0)

        if gpa < 1.25:
            risk_factors.append(f"GPA of {gpa:.2f} is below the 1.25 critical threshold")
            score = max(score, 80.0)

        # attendance check
        if attendance < 75:
            factor_severity = "severely" if attendance < 50 else "significantly"
            risk_factors.append(f"Attendance is {factor_severity} low at {attendance:.1f}%")
            # max penalty reached at 50% attendance
            penalty = min(1.0, (75 - attendance) / 25.0)
            score += penalty * 30

        # GPA check
        if gpa < 2.0:
            risk_factors.append(f"GPA of {gpa:.2f} is below the 2.0 minimum threshold")
            # max penalty reached at 1.0 GPA
            penalty = min(1.0, (2.0 - gpa) / 1.0)
            score += penalty * 60

        # late submissions check
        if late_pct > 30:
            risk_factors.append(f"{late_pct:.1f}% of submissions were turned in late")
            # max penalty reached at 60% late submissions
            penalty = min(1.0, (late_pct - 30) / 30.0)
            score += penalty * 10

        # determine the overall risk level from the composite score
        score = min(score, 100)
        if score >= 70:
            level = "critical"
        elif score >= 50:
            level = "high"
        elif score >= 25:
            level = "medium"
        elif score > 0:
            level = "low"
        else:
            level = "none"

        summary = self._build_summary(student_data, risk_factors, level)
        advice = "Schedule a brief meeting to discuss their current challenges and identify areas where they can improve their habits." if level != "none" else "Keep up the good work!"

        return RiskAssessment(
            risk_level=level,
            risk_score=round(score, 1),
            risk_factors=risk_factors,
            summary=summary,
            advice=advice,
        )

    def suggest_intervention(self, risk_data: dict) -> InterventionSuggestion:
        risk_type = risk_data.get("primary_risk_type", "academic")
        severity = risk_data.get("severity", "medium")

        recommendations = {
            "attendance": {
                "recommendation": "Schedule a one-on-one meeting to understand attendance barriers. "
                                  "Consider flexible attendance options if valid reasons exist. "
                                  "Set up a weekly check-in schedule.",
                "reasoning": "Consistent attendance strongly correlates with academic success. "
                             "Early intervention on attendance issues prevents cascading academic problems.",
            },
            "academic": {
                "recommendation": "Arrange peer tutoring for weak courses. "
                                  "Connect student with academic support center. "
                                  "Create a structured study plan with weekly milestones.",
                "reasoning": "Academic decline often stems from gaps in foundational concepts. "
                             "Targeted support in specific weak areas is more effective than general advice.",
            },
            "submission": {
                "recommendation": "Help student set up a personal deadline tracking system. "
                                  "Break larger assignments into smaller deliverables. "
                                  "Check for external factors affecting time management.",
                "reasoning": "Late submission patterns usually indicate time management or workload issues "
                             "rather than lack of ability. Structural support is more effective than penalties.",
            },
        }

        rec = recommendations.get(risk_type, recommendations["academic"])

        return InterventionSuggestion(
            intervention_type=risk_type,
            recommendation=rec["recommendation"],
            reasoning=rec["reasoning"],
            priority=severity,
        )

    def explain_reasoning(self, analysis: dict) -> str:
        factors = analysis.get("risk_factors", [])
        if not factors:
            return "No significant risk factors detected. Student appears to be on track."

        explanation = "Based on the analysis:\n"
        for i, factor in enumerate(factors, 1):
            explanation += f"{i}. {factor}\n"
        explanation += "\nThese factors combined suggest the student may need additional support."
        return explanation

    def _build_summary(self, data: dict, factors: list, level: str) -> str:
        name = data.get("name", "Student")
        if level == "none":
            return f"{name} is performing well across all metrics. No intervention needed."
        elif level == "low":
            return f"{name} shows minor concerns that should be monitored. No immediate action required."
        elif level == "medium":
            return f"{name} has declining metrics that need attention. Proactive intervention recommended."
        elif level == "high":
            return f"{name} is showing significant risk signals. Immediate intervention recommended."
        else:
            return f"{name} is in critical academic danger. Urgent intervention required across multiple areas."
