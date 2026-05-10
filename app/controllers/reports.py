from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    Student, Alert, Intervention, RiskLevel, AlertType,
    InterventionStatus, InterventionType,
)

router = APIRouter(prefix="/reports")
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def reports_overview(request: Request, db: Session = Depends(get_db)):
    # class-wide stats
    total = db.query(Student).count()
    risk_counts = {}
    for level in RiskLevel:
        risk_counts[level.value] = db.query(Student).filter(Student.risk_level == level).count()

    # alert stats
    total_alerts = db.query(Alert).count()
    alert_by_type = {}
    for t in AlertType:
        alert_by_type[t.value] = db.query(Alert).filter(Alert.type == t).count()

    # intervention stats
    total_interventions = db.query(Intervention).count()
    intervention_status = {}
    for s in InterventionStatus:
        intervention_status[s.value] = db.query(Intervention).filter(Intervention.status == s).count()

    # GPA distribution buckets
    gpa_dist = {
        "3.5-4.0": db.query(Student).filter(Student.overall_gpa >= 3.5).count(),
        "3.0-3.5": db.query(Student).filter(Student.overall_gpa >= 3.0, Student.overall_gpa < 3.5).count(),
        "2.5-3.0": db.query(Student).filter(Student.overall_gpa >= 2.5, Student.overall_gpa < 3.0).count(),
        "2.0-2.5": db.query(Student).filter(Student.overall_gpa >= 2.0, Student.overall_gpa < 2.5).count(),
        "<2.0": db.query(Student).filter(Student.overall_gpa < 2.0).count(),
    }

    # attendance distribution
    att_dist = {
        "90-100%": db.query(Student).filter(Student.attendance_percentage >= 90).count(),
        "75-90%": db.query(Student).filter(Student.attendance_percentage >= 75, Student.attendance_percentage < 90).count(),
        "60-75%": db.query(Student).filter(Student.attendance_percentage >= 60, Student.attendance_percentage < 75).count(),
        "below 60%": db.query(Student).filter(Student.attendance_percentage < 60).count(),
    }

    # section comparison
    sections = db.query(Student.section, func.avg(Student.overall_gpa), func.avg(Student.attendance_percentage)) \
        .group_by(Student.section).all()
    section_data = [{"section": s[0], "avg_gpa": round(s[1], 2), "avg_attendance": round(s[2], 1)} for s in sections]

    unread_alerts = db.query(Alert).filter(Alert.is_read == False).count()

    return templates.TemplateResponse(request, "reports.html", context={
        "total_students": total,
        "risk_counts": risk_counts,
        "total_alerts": total_alerts,
        "alert_by_type": alert_by_type,
        "total_interventions": total_interventions,
        "intervention_status": intervention_status,
        "gpa_distribution": gpa_dist,
        "attendance_distribution": att_dist,
        "section_data": section_data,
        "active_page": "reports",
        "unread_alerts": unread_alerts,
    })
