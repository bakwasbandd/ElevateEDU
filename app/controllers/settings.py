from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Alert
from app.services.monitoring_engine import MonitoringEngine
from app.services.data_seeder import seed_database
from app.config import config

router = APIRouter(prefix="/settings")
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def settings_page(request: Request, db: Session = Depends(get_db)):
    engine = MonitoringEngine()
    unread_alerts = db.query(Alert).filter(Alert.is_read == False).count()

    return templates.TemplateResponse(request, "settings.html", context={
        "active_page": "settings",
        "current_strategy": engine.current_strategy,
        "config": config,
        "unread_alerts": unread_alerts,
    })


@router.post("/ai-strategy")
def switch_ai_strategy(strategy: str = Form(...)):
    """Swap the AI strategy at runtime — no restart needed."""
    engine = MonitoringEngine()
    engine.switch_strategy(strategy)
    config.AI_STRATEGY = strategy
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/thresholds")
def update_thresholds(
    attendance: float = Form(...),
    gpa: float = Form(...),
    late_submission: float = Form(...),
):
    config.ATTENDANCE_RISK_THRESHOLD = attendance
    config.GPA_RISK_THRESHOLD = gpa
    config.LATE_SUBMISSION_THRESHOLD = late_submission

    # re-create the monitoring engine observers with new thresholds
    from app.patterns.singleton import SingletonMeta
    SingletonMeta.reset(MonitoringEngine)

    return RedirectResponse(url="/settings", status_code=303)


@router.post("/reseed")
def reseed_data(db: Session = Depends(get_db)):
    """Regenerate all synthetic data."""
    count = seed_database(db, config.NUM_STUDENTS)
    return RedirectResponse(url="/settings", status_code=303)
