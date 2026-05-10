from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import random
from app.database import get_db
from app.models import Alert, AlertType, AlertSeverity, Student, Intervention, InterventionType, InterventionStatus
from app.services.monitoring_engine import MonitoringEngine
from typing import Optional

router = APIRouter(prefix="/alerts")
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def alert_list(
    request: Request,
    db: Session = Depends(get_db),
    alert_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    query = db.query(Alert)

    if alert_type and alert_type != "all":
        query = query.filter(Alert.type == AlertType(alert_type))
    if severity and severity != "all":
        query = query.filter(Alert.severity == AlertSeverity(severity))
    if status == "unread":
        query = query.filter(Alert.is_read == False)
    elif status == "read":
        query = query.filter(Alert.is_read == True)

    alerts = query.order_by(Alert.created_at.desc()).all()

    if status == "resolved":
        alerts = [
            alert for alert in alerts
            if any(iv.status == InterventionStatus.COMPLETED for iv in alert.interventions)
        ]
    else:
        # hide alerts that already have a completed intervention
        alerts = [
            alert for alert in alerts
            if not any(iv.status == InterventionStatus.COMPLETED for iv in alert.interventions)
        ]

    # attach student names and group them
    student_ids = {a.student_id for a in alerts}
    students = {s.id: s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()}
    
    temp_groups = {}
    for alert in alerts:
        student = students.get(alert.student_id)
        if not student:
            continue
        alert._student = student
        if student.id not in temp_groups:
            temp_groups[student.id] = {"student": student, "alerts": []}
        temp_groups[student.id]["alerts"].append(alert)

    grouped_alerts = list(temp_groups.values())

    unread_alerts = db.query(Alert).filter(Alert.is_read == False).count()

    return templates.TemplateResponse(request, "alerts.html", context={
        "alerts": alerts,
        "grouped_alerts": grouped_alerts,
        "active_page": "alerts",
        "current_type": alert_type or "all",
        "current_severity": severity or "all",
        "current_status": status or "all",
        "unread_alerts": unread_alerts,
    })


@router.post("/mark-all-read")
def mark_all_read(db: Session = Depends(get_db)):
    db.query(Alert).filter(Alert.is_read == False).update({"is_read": True})
    db.commit()
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/run-scan")
def run_scan(db: Session = Depends(get_db)):
    """Trigger the monitoring engine to scan all students."""
    engine = MonitoringEngine()
    engine.run_scan(db)
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.is_read = True
        db.commit()
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/{alert_id}/intervene")
def intervene(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return RedirectResponse(url="/alerts", status_code=303)

    intervention_type_map = {
        AlertType.ATTENDANCE: InterventionType.ATTENDANCE,
        AlertType.ACADEMIC: InterventionType.ACADEMIC,
        AlertType.SUBMISSION: InterventionType.SUBMISSION,
    }
    intervention_type = intervention_type_map.get(alert.type, InterventionType.ACADEMIC)

    intervention = db.query(Intervention).filter(
        Intervention.alert_id == alert.id,
    ).first()

    if intervention:
        intervention.status = InterventionStatus.IN_PROGRESS
    else:
        intervention = Intervention(
            student_id=alert.student_id,
            alert_id=alert.id,
            type=intervention_type,
            recommendation=f"Review and address the {alert.type.value} alert for {alert.student.name}.",
            ai_reasoning=alert.message,
            status=InterventionStatus.IN_PROGRESS,
        )
        db.add(intervention)

    db.commit()
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/{alert_id}/complete")
def complete_intervention(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return RedirectResponse(url="/alerts", status_code=303)

    intervention_type_map = {
        AlertType.ATTENDANCE: InterventionType.ATTENDANCE,
        AlertType.ACADEMIC: InterventionType.ACADEMIC,
        AlertType.SUBMISSION: InterventionType.SUBMISSION,
    }
    intervention_type = intervention_type_map.get(alert.type, InterventionType.ACADEMIC)

    intervention = db.query(Intervention).filter(
        Intervention.alert_id == alert.id,
    ).first()
    if intervention:
        intervention.status = InterventionStatus.COMPLETED
    else:
        intervention = db.query(Intervention).filter(
            Intervention.student_id == alert.student_id,
            Intervention.type == intervention_type,
        ).order_by(Intervention.created_at.desc()).first()
        if intervention:
            intervention.status = InterventionStatus.COMPLETED

    student = db.query(Student).filter(Student.id == alert.student_id).first()
    if student:
        improved_gpa = random.gauss(2.45, 0.28)
        student.overall_gpa = round(max(2.05, min(3.10, improved_gpa)), 2)

    alert.is_read = True
    db.commit()
    return RedirectResponse(url="/alerts", status_code=303)
