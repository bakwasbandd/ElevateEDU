"""
BEFORE REFACTORING — monolithic_app.py

This is a deliberately messy, monolithic implementation of the student risk monitoring system.
Everything is in a single file with no design patterns, no separation of concerns, and no modularity.

This exists to demonstrate WHY design patterns matter. Compare this with the 'app/' directory
to see how Observer, Strategy, Factory, and Singleton+MVC improve the codebase.

PROBLEMS WITH THIS APPROACH:
1. No separation of concerns — models, logic, routes all mixed together
2. Hardcoded AI logic — can't swap between different AI engines
3. Manual if/else chains instead of Observer pattern
4. Inline intervention creation instead of Factory pattern
5. Global mutable state instead of Singleton
6. Duplicated threshold checking code
7. No way to test individual components
8. Adding a new risk type requires changes in multiple places
"""

from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import random

# === EVERYTHING CRAMMED INTO ONE FILE ===

app = FastAPI()
templates = Jinja2Templates(directory="templates")

engine = create_engine("sqlite:///./monolithic.db")
Session = sessionmaker(bind=engine)
Base = declarative_base()

# global mutable state — bad practice
ATTENDANCE_THRESHOLD = 75.0
GPA_THRESHOLD = 2.0
LATE_THRESHOLD = 30.0
current_ai_mode = "mock"  # can't swap cleanly


# models jammed in same file
class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    attendance_pct = Column(Float, default=100)
    gpa = Column(Float, default=4.0)
    late_pct = Column(Float, default=0)
    risk = Column(String, default="none")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer)
    message = Column(String)
    alert_type = Column(String)
    severity = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)


# no observer pattern — just a massive function with if/else
def check_student_risks(student):
    alerts = []

    # attendance check — duplicated logic
    if student.attendance_pct < ATTENDANCE_THRESHOLD:
        if student.attendance_pct < 50:
            sev = "critical"
        elif student.attendance_pct < 65:
            sev = "high"
        else:
            sev = "medium"
        alerts.append({
            "type": "attendance",
            "severity": sev,
            "message": f"Attendance at {student.attendance_pct}%"
        })

    # gpa check — same pattern copy-pasted
    if student.gpa < GPA_THRESHOLD:
        if student.gpa < 1.0:
            sev = "critical"
        elif student.gpa < 1.5:
            sev = "high"
        else:
            sev = "medium"
        alerts.append({
            "type": "academic",
            "severity": sev,
            "message": f"GPA at {student.gpa}"
        })

    # late submission check — again, same thing
    if student.late_pct > LATE_THRESHOLD:
        if student.late_pct > 60:
            sev = "critical"
        elif student.late_pct > 45:
            sev = "high"
        else:
            sev = "medium"
        alerts.append({
            "type": "submission",
            "severity": sev,
            "message": f"{student.late_pct}% late submissions"
        })

    return alerts


# no strategy pattern — hardcoded AI logic, can't swap engines
def get_ai_recommendation(student, alert_type):
    global current_ai_mode

    # only mock works — no clean way to add cloud or local
    if current_ai_mode == "mock":
        if alert_type == "attendance":
            return "Schedule meeting about attendance"
        elif alert_type == "academic":
            return "Arrange tutoring sessions"
        elif alert_type == "submission":
            return "Set up deadline reminders"
        else:
            return "Review student profile"
    elif current_ai_mode == "cloud":
        # would need to copy-paste all the same logic here
        # with API calls mixed in — not maintainable
        return "Cloud AI not properly integrated"
    else:
        return "Unknown AI mode"


# no factory pattern — inline creation with duplicated fields
def create_intervention(student, alert_type, severity):
    recommendation = get_ai_recommendation(student, alert_type)

    # all intervention types look the same — no typed structure
    return {
        "student_id": student.id,
        "student_name": student.name,
        "type": alert_type,
        "severity": severity,
        "recommendation": recommendation,
        "reasoning": "Because thresholds were exceeded",  # no real AI reasoning
        "created_at": datetime.utcnow(),
    }


# run scan — everything in one giant function
def run_full_scan():
    db = Session()
    students = db.query(Student).all()
    all_alerts = []
    all_interventions = []

    for student in students:
        # check risks (no observer)
        alerts = check_student_risks(student)

        for alert_data in alerts:
            # save alert directly (no clean model)
            alert = Alert(
                student_id=student.id,
                message=alert_data["message"],
                alert_type=alert_data["type"],
                severity=alert_data["severity"],
            )
            db.add(alert)
            all_alerts.append(alert_data)

            # create intervention inline (no factory)
            intervention = create_intervention(student, alert_data["type"], alert_data["severity"])
            all_interventions.append(intervention)

        # update risk level — manual calculation
        if any(a["severity"] == "critical" for a in alerts):
            student.risk = "critical"
        elif any(a["severity"] == "high" for a in alerts):
            student.risk = "high"
        elif any(a["severity"] == "medium" for a in alerts):
            student.risk = "medium"
        elif alerts:
            student.risk = "low"
        else:
            student.risk = "none"

    db.commit()
    db.close()
    return {"alerts": len(all_alerts), "interventions": len(all_interventions)}


# routes mixed with business logic
@app.get("/")
def dashboard(request: Request):
    db = Session()
    students = db.query(Student).all()
    total = len(students)
    at_risk = sum(1 for s in students if s.risk in ["medium", "high", "critical"])
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(10).all()
    db.close()
    return {"total": total, "at_risk": at_risk, "alerts": len(alerts)}


@app.post("/scan")
def scan():
    return run_full_scan()


@app.post("/switch-ai")
def switch_ai(mode: str):
    global current_ai_mode
    current_ai_mode = mode  # no validation, no clean interface
    return {"mode": current_ai_mode}


"""
SUMMARY OF PROBLEMS:
- 200+ lines and already hard to follow
- Adding a new risk type (e.g., engagement) means editing 3+ functions
- No way to unit test individual components
- AI logic is hardcoded — can't swap providers without rewriting
- No typed models for interventions — just dicts
- Global mutable state is error-prone
- Code duplication everywhere (severity calculation repeated 3 times)
- No clean MVC separation — routes know about business logic

SEE: app/ directory for the refactored version using:
- Observer Pattern: StudentDataMonitor with pluggable observers
- Strategy Pattern: AIStrategy interface with Mock/Cloud/Local implementations
- Factory Pattern: InterventionFactory producing typed intervention objects
- Singleton + MVC: Clean separation with a single MonitoringEngine
"""
