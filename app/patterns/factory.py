from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InterventionReport:
    """Base intervention report that all types share."""
    student_id: int
    student_name: str
    intervention_type: str
    severity: str
    recommendation: str
    action_items: list[str]
    ai_reasoning: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AttendanceIntervention(InterventionReport):
    current_attendance: float = 0.0
    target_attendance: float = 75.0
    missed_classes: int = 0


@dataclass
class AcademicIntervention(InterventionReport):
    current_gpa: float = 0.0
    weak_courses: list[str] = field(default_factory=list)
    suggested_resources: list[str] = field(default_factory=list)


@dataclass
class SubmissionIntervention(InterventionReport):
    late_percentage: float = 0.0
    missed_deadlines: int = 0
    upcoming_deadlines: list[str] = field(default_factory=list)


class InterventionFactory:
    """Creates the right type of intervention based on risk classification."""

    @staticmethod
    def create(risk_type: str, student_data: dict, recommendation: str,
               ai_reasoning: str, severity: str = "medium") -> InterventionReport:

        base_kwargs = {
            "student_id": student_data.get("student_id", 0),
            "student_name": student_data.get("name", "Unknown"),
            "severity": severity,
            "recommendation": recommendation,
            "ai_reasoning": ai_reasoning,
        }

        if risk_type == "attendance":
            return AttendanceIntervention(
                **base_kwargs,
                intervention_type="attendance",
                action_items=[
                    "Schedule meeting with student to discuss attendance",
                    "Set up weekly attendance check-ins",
                    "Connect with student advisor",
                ],
                current_attendance=student_data.get("attendance_percentage", 0),
                missed_classes=student_data.get("missed_classes", 0),
            )

        elif risk_type == "academic":
            return AcademicIntervention(
                **base_kwargs,
                intervention_type="academic",
                action_items=[
                    "Arrange tutoring sessions for weak courses",
                    "Review study habits with academic counselor",
                    "Create a structured revision plan",
                ],
                current_gpa=student_data.get("gpa", 0),
                weak_courses=student_data.get("weak_courses", []),
                suggested_resources=["Khan Academy", "Course office hours", "Peer study groups"],
            )

        elif risk_type == "submission":
            return SubmissionIntervention(
                **base_kwargs,
                intervention_type="submission",
                action_items=[
                    "Set up deadline reminders",
                    "Break assignments into smaller milestones",
                    "Check for workload management issues",
                ],
                late_percentage=student_data.get("late_submission_percentage", 0),
                missed_deadlines=student_data.get("missed_deadlines", 0),
            )

        # fallback — generic intervention
        return InterventionReport(
            **base_kwargs,
            intervention_type=risk_type,
            action_items=["Review student's overall academic profile"],
        )
