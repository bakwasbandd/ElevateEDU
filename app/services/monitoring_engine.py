from sqlalchemy.orm import Session
from app.patterns.singleton import SingletonMeta
from app.patterns.observer import StudentDataMonitor, AttendanceObserver, GradeObserver, SubmissionObserver
from app.patterns.strategy import RiskAnalysisContext
from app.patterns.factory import InterventionFactory
from app.ai import get_strategy
from app.models import Student, Alert, AlertType, AlertSeverity, Intervention, InterventionType, InterventionStatus
from app.services.risk_engine import compute_student_metrics, compute_risk_level, get_primary_risk_type
from app.config import config


class MonitoringEngine(metaclass=SingletonMeta):
    """The brain of the system — singleton that ties Observer, Strategy, and Factory together.
    Runs analysis on all students, generates alerts and interventions.
    """

    def __init__(self):
        # set up the observer pipeline
        self.monitor = StudentDataMonitor()
        self.monitor.attach(AttendanceObserver(config.ATTENDANCE_RISK_THRESHOLD))
        self.monitor.attach(GradeObserver(config.GPA_RISK_THRESHOLD))
        self.monitor.attach(SubmissionObserver(config.LATE_SUBMISSION_THRESHOLD))

        # set up the AI strategy
        strategy = get_strategy(config.AI_STRATEGY)
        self.risk_context = RiskAnalysisContext(strategy)

        # factory for creating interventions
        self.factory = InterventionFactory()

    def switch_strategy(self, strategy_name: str):
        """Swap the AI strategy at runtime — the whole point of Strategy pattern."""
        strategy = get_strategy(strategy_name)
        self.risk_context.set_strategy(strategy)

    @property
    def current_strategy(self) -> str:
        return self.risk_context.strategy_name

    def run_scan(self, db: Session) -> dict:
        """Run a full scan across all students. Returns a summary of what was found."""
        
        # Save current strategy and switch to mock for bulk processing speed
        original_strategy_name = self.current_strategy
        self.switch_strategy("mock")
        
        students = db.query(Student).all()
        scan_results = {
            "students_scanned": 0,
            "alerts_generated": 0,
            "interventions_created": 0,
        }

        for student in students:
            metrics = compute_student_metrics(db, student)
            result = self._analyze_student(db, student, metrics)
            scan_results["students_scanned"] += 1
            scan_results["alerts_generated"] += result["alerts"]
            scan_results["interventions_created"] += result["interventions"]

        # Restore original strategy
        if "Cloud" in original_strategy_name:
            self.switch_strategy("cloud")
        elif "Local" in original_strategy_name:
            self.switch_strategy("local")
        else:
            self.switch_strategy("mock")

        db.commit()
        return scan_results

    def analyze_single_student(self, db: Session, student: Student) -> dict:
        """Run analysis on one student — used for the detail view."""
        metrics = compute_student_metrics(db, student)

        # get the AI's take
        risk_assessment = self.risk_context.analyze(metrics)

        # update the student's risk level
        student.risk_level = compute_risk_level(risk_assessment.risk_score, metrics["gpa"])
        db.commit()

        return {
            "metrics": metrics,
            "risk_assessment": {
                "risk_level": risk_assessment.risk_level,
                "risk_score": risk_assessment.risk_score,
                "risk_factors": risk_assessment.risk_factors,
                "summary": risk_assessment.summary,
                "advice": risk_assessment.advice,
            },
            "strategy_used": self.current_strategy,
        }

    def _analyze_student(self, db: Session, student: Student, metrics: dict) -> dict:
        """Internal: run the full pipeline on one student."""
        result = {"alerts": 0, "interventions": 0}

        # step 1: Observer pattern — check thresholds
        observer_alerts = self.monitor.analyze_student(metrics)

        # step 2: Strategy pattern — AI risk analysis
        risk_assessment = self.risk_context.analyze(metrics)

        # update student risk level
        student.risk_level = compute_risk_level(risk_assessment.risk_score, metrics["gpa"])

        # step 3: create alerts from observer results using overall severity
        overall_severity = risk_assessment.risk_level
        
        if observer_alerts and overall_severity != "none":
            created_alerts = []
            for alert_data in observer_alerts:
                existing_alert = db.query(Alert).filter(
                    Alert.student_id == student.id,
                    Alert.type == AlertType(alert_data["type"])
                ).first()

                if existing_alert:
                    existing_alert.message = alert_data["message"]
                    existing_alert.severity = AlertSeverity(overall_severity)
                    created_alerts.append(existing_alert)
                else:
                    alert = Alert(
                        student_id=student.id,
                        type=AlertType(alert_data["type"]),
                        severity=AlertSeverity(overall_severity),
                        message=alert_data["message"],
                    )
                    db.add(alert)
                    db.flush()
                    created_alerts.append(alert)
                    result["alerts"] += 1

            # step 4: Strategy + Factory — get AI intervention and wrap it
            primary_type = get_primary_risk_type(metrics)
            risk_data = {
                "primary_risk_type": primary_type,
                "severity": overall_severity,
                "risk_factors": risk_assessment.risk_factors,
                "student_name": student.name,
            }
            suggestion = self.risk_context.suggest(risk_data)

            # Factory creates the typed intervention
            report = self.factory.create(
                risk_type=primary_type,
                student_data=metrics,
                recommendation=suggestion.recommendation,
                ai_reasoning=suggestion.reasoning,
                severity=overall_severity,
            )

            # link intervention to the primary alert created
            if created_alerts:
                existing_intervention = db.query(Intervention).filter(
                    Intervention.student_id == student.id,
                    Intervention.type == InterventionType(primary_type)
                ).first()

                if existing_intervention:
                    existing_intervention.recommendation = report.recommendation
                    existing_intervention.ai_reasoning = report.ai_reasoning
                else:
                    intervention = Intervention(
                        student_id=student.id,
                        alert_id=created_alerts[0].id,
                        type=InterventionType(primary_type),
                        recommendation=report.recommendation,
                        ai_reasoning=report.ai_reasoning,
                        status=InterventionStatus.PENDING,
                    )
                    db.add(intervention)
                    result["interventions"] += 1

        return result
