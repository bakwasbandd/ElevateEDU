from sqlalchemy.orm import Session
from app.models import Student, Attendance, Assessment, AttendanceStatus, RiskLevel
from app.config import config


def compute_student_metrics(db: Session, student: Student) -> dict:
    """Pull all data for a student and compute their risk metrics."""

    # attendance
    records = db.query(Attendance).filter(Attendance.student_id == student.id).all()
    total = len(records)
    present = sum(1 for r in records if r.status != AttendanceStatus.ABSENT)
    attendance_pct = (present / max(total, 1)) * 100

    # assessments
    assessments = db.query(Assessment).filter(Assessment.student_id == student.id).all()
    total_assessments = len(assessments)
    late_count = sum(1 for a in assessments if a.is_late)
    late_pct = (late_count / max(total_assessments, 1)) * 100

    # per-course performance
    course_scores = {}
    for a in assessments:
        if a.course not in course_scores:
            course_scores[a.course] = {"total_score": 0, "total_max": 0}
        course_scores[a.course]["total_score"] += a.score
        course_scores[a.course]["total_max"] += a.max_score

    weak_courses = []
    for course, data in course_scores.items():
        pct = (data["total_score"] / max(data["total_max"], 1)) * 100
        if pct < 50:
            weak_courses.append(course)

    return {
        "student_id": student.id,
        "name": student.name,
        "roll_number": student.roll_number,
        "attendance_percentage": round(attendance_pct, 1),
        "gpa": student.overall_gpa,
        "late_submission_percentage": round(late_pct, 1),
        "total_assessments": total_assessments,
        "late_count": late_count,
        "missed_classes": total - present,
        "weak_courses": weak_courses,
        "course_scores": {
            c: round((d["total_score"] / max(d["total_max"], 1)) * 100, 1)
            for c, d in course_scores.items()
        },
    }


def compute_risk_level(risk_score: float, gpa: float | None = None) -> RiskLevel:
    """Map a numeric score to a risk level enum."""
    if gpa is not None and gpa < 1.25:
        return RiskLevel.CRITICAL
    if risk_score >= 70:
        return RiskLevel.CRITICAL
    elif risk_score >= 50:
        return RiskLevel.HIGH
    elif risk_score >= 25:
        return RiskLevel.MEDIUM
    elif risk_score > 0:
        return RiskLevel.LOW
    return RiskLevel.NONE


def get_primary_risk_type(metrics: dict) -> str:
    """Figure out what the biggest problem area is."""
    scores = {
        "attendance": max(0, (config.ATTENDANCE_RISK_THRESHOLD - metrics["attendance_percentage"])) * config.ATTENDANCE_WEIGHT,
        "academic": max(0, (config.GPA_RISK_THRESHOLD - metrics["gpa"]) * 20) * config.ACADEMIC_WEIGHT,
        "submission": max(0, (metrics["late_submission_percentage"] - config.LATE_SUBMISSION_THRESHOLD)) * config.SUBMISSION_WEIGHT,
    }
    return max(scores, key=scores.get)
