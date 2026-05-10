from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import random
from app.database import get_db
from app.models import Student, Alert, Intervention, Assessment, Attendance, RiskLevel, AttendanceStatus
from app.models import InterventionStatus
from app.services.monitoring_engine import MonitoringEngine
from app.services.risk_engine import compute_student_metrics
from typing import Optional

router = APIRouter(prefix="/students")
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def student_list(
    request: Request,
    db: Session = Depends(get_db),
    risk: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    query = db.query(Student)

    if risk and risk != "all":
        query = query.filter(Student.risk_level == RiskLevel(risk))
    if section and section != "all":
        query = query.filter(Student.section == section)
    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))

    students = query.order_by(Student.name).all()
    unread_alerts = db.query(Alert).filter(Alert.is_read == False).count()

    return templates.TemplateResponse(request, "students.html", context={
        "students": students,
        "active_page": "students",
        "current_risk": risk or "all",
        "current_section": section or "all",
        "current_search": search or "",
        "unread_alerts": unread_alerts,
    })


@router.get("/{student_id}")
def student_detail(request: Request, student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return templates.TemplateResponse(request, "404.html", status_code=404)

    # run AI analysis
    engine = MonitoringEngine()
    analysis = engine.analyze_single_student(db, student)
    metrics = analysis["metrics"]

    # alerts for this student
    alerts = (
        db.query(Alert).filter(Alert.student_id == student_id)
        .order_by(Alert.created_at.desc()).limit(20).all()
    )

    # interventions
    interventions = (
        db.query(Intervention).filter(Intervention.student_id == student_id)
        .order_by(Intervention.created_at.desc()).limit(10).all()
    )

    # attendance breakdown per course
    attendance_records = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    course_attendance = {}
    for rec in attendance_records:
        if rec.course not in course_attendance:
            course_attendance[rec.course] = {"present": 0, "absent": 0, "late": 0, "total": 0}
        course_attendance[rec.course]["total"] += 1
        if rec.status == AttendanceStatus.PRESENT:
            course_attendance[rec.course]["present"] += 1
        elif rec.status == AttendanceStatus.ABSENT:
            course_attendance[rec.course]["absent"] += 1
        else:
            course_attendance[rec.course]["late"] += 1

    # assessment scores per course
    assessments = db.query(Assessment).filter(Assessment.student_id == student_id).all()
    course_assessments = {}
    for a in assessments:
        if a.course not in course_assessments:
            course_assessments[a.course] = []
        course_assessments[a.course].append({
            "title": a.title, "type": a.type.value,
            "score": a.score, "max_score": a.max_score,
            "percentage": round((a.score / max(a.max_score, 1)) * 100, 1),
            "is_late": a.is_late,
        })

    unread_alerts = db.query(Alert).filter(Alert.is_read == False).count()

    return templates.TemplateResponse(request, "student_detail.html", context={
        "student": student,
        "metrics": metrics,
        "risk_assessment": analysis["risk_assessment"],
        "strategy_used": analysis["strategy_used"],
        "alerts": alerts,
        "interventions": interventions,
        "course_attendance": course_attendance,
        "course_assessments": course_assessments,
        "active_page": "students",
        "unread_alerts": unread_alerts,
    })


@router.post("/{student_id}/interventions/{intervention_id}/start")
def start_intervention(student_id: int, intervention_id: int, db: Session = Depends(get_db)):
    intervention = db.query(Intervention).filter(
        Intervention.id == intervention_id,
        Intervention.student_id == student_id,
    ).first()

    if intervention and intervention.status == InterventionStatus.PENDING:
        intervention.status = InterventionStatus.IN_PROGRESS
        db.commit()

    return RedirectResponse(url=f"/students/{student_id}", status_code=303)


@router.post("/{student_id}/interventions/{intervention_id}/complete")
def complete_intervention(student_id: int, intervention_id: int, db: Session = Depends(get_db)):
    intervention = db.query(Intervention).filter(
        Intervention.id == intervention_id,
        Intervention.student_id == student_id,
    ).first()

    if intervention and intervention.status != InterventionStatus.COMPLETED:
        intervention.status = InterventionStatus.COMPLETED

        student = db.query(Student).filter(Student.id == student_id).first()
        if student:
            improved_gpa = random.gauss(2.45, 0.28)
            student.overall_gpa = round(max(2.05, min(3.10, improved_gpa)), 2)

        if intervention.alert_id:
            alert = db.query(Alert).filter(Alert.id == intervention.alert_id).first()
            if alert:
                alert.is_read = True

        db.commit()

    return RedirectResponse(url=f"/students/{student_id}", status_code=303)
