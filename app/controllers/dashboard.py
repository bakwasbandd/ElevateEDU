from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Student, Alert, RiskLevel, AlertSeverity

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    total_students = db.query(Student).count()
    at_risk = db.query(Student).filter(Student.risk_level.in_([
        RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL
    ])).count()
    critical = db.query(Student).filter(Student.risk_level == RiskLevel.CRITICAL).count()

    avg_gpa = db.query(func.avg(Student.overall_gpa)).scalar() or 0
    avg_attendance = db.query(func.avg(Student.attendance_percentage)).scalar() or 0

    # risk distribution for the pie chart
    risk_dist = {}
    for level in RiskLevel:
        count = db.query(Student).filter(Student.risk_level == level).count()
        risk_dist[level.value] = count

    # recent alerts
    recent_alerts = (
        db.query(Alert).order_by(Alert.created_at.desc()).limit(10).all()
    )

    # top at-risk students
    top_risk = (
        db.query(Student)
        .filter(Student.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL]))
        .order_by(Student.overall_gpa.asc())
        .limit(10)
        .all()
    )

    unread_alerts = db.query(Alert).filter(Alert.is_read == False).count()

    return templates.TemplateResponse(request, "dashboard.html", context={
        "total_students": total_students,
        "at_risk": at_risk,
        "critical": critical,
        "avg_gpa": round(avg_gpa, 2),
        "avg_attendance": round(avg_attendance, 1),
        "risk_distribution": risk_dist,
        "recent_alerts": recent_alerts,
        "top_risk_students": top_risk,
        "unread_alerts": unread_alerts,
        "active_page": "dashboard",
    })
