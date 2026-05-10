from abc import ABC, abstractmethod
from typing import Any


class Observer(ABC):
    """Base observer — gets notified when something changes."""

    @abstractmethod
    def update(self, event_type: str, data: dict) -> dict | None:
        pass


class Subject(ABC):
    """Base subject — maintains a list of observers and notifies them."""

    def __init__(self):
        self._observers: list[Observer] = []

    def attach(self, observer: Observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer):
        self._observers.remove(observer)

    def notify(self, event_type: str, data: dict) -> list[dict]:
        """Notify all observers and collect any alerts they produce."""
        results = []
        for observer in self._observers:
            result = observer.update(event_type, data)
            if result:
                results.append(result)
        return results


# --- Concrete Observers ---

class AttendanceObserver(Observer):
    """Watches for attendance dropping below the threshold."""

    def __init__(self, threshold: float = 75.0):
        self.threshold = threshold

    def update(self, event_type: str, data: dict) -> dict | None:
        if event_type != "student_analysis":
            return None

        attendance_pct = data.get("attendance_percentage", 100)
        if attendance_pct >= self.threshold:
            return None

        severity = "critical" if attendance_pct < 50 else "high" if attendance_pct < 65 else "medium"
        return {
            "type": "attendance",
            "severity": severity,
            "message": f"Attendance at {attendance_pct:.1f}% — below {self.threshold}% threshold",
            "student_id": data.get("student_id"),
        }


class GradeObserver(Observer):
    """Watches for GPA falling below the threshold."""

    def __init__(self, threshold: float = 2.0):
        self.threshold = threshold

    def update(self, event_type: str, data: dict) -> dict | None:
        if event_type != "student_analysis":
            return None

        gpa = data.get("gpa", 4.0)
        if gpa >= self.threshold:
            return None

        severity = "critical" if gpa < 1.0 else "high" if gpa < 1.5 else "medium"
        return {
            "type": "academic",
            "severity": severity,
            "message": f"GPA at {gpa:.2f} — below {self.threshold} threshold",
            "student_id": data.get("student_id"),
        }


class SubmissionObserver(Observer):
    """Watches for too many late submissions."""

    def __init__(self, threshold: float = 30.0):
        self.threshold = threshold

    def update(self, event_type: str, data: dict) -> dict | None:
        if event_type != "student_analysis":
            return None

        late_pct = data.get("late_submission_percentage", 0)
        if late_pct <= self.threshold:
            return None

        severity = "critical" if late_pct > 60 else "high" if late_pct > 45 else "medium"
        return {
            "type": "submission",
            "severity": severity,
            "message": f"{late_pct:.1f}% of submissions are late — exceeds {self.threshold}% limit",
            "student_id": data.get("student_id"),
        }


class StudentDataMonitor(Subject):
    """The central subject that observers subscribe to.
    Feed it student data and it'll notify all observers automatically.
    """

    def analyze_student(self, student_data: dict) -> list[dict]:
        return self.notify("student_analysis", student_data)
