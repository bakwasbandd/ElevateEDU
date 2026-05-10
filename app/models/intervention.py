from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum


class InterventionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class InterventionType(str, enum.Enum):
    ATTENDANCE = "attendance"
    ACADEMIC = "academic"
    SUBMISSION = "submission"


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    type = Column(SAEnum(InterventionType), nullable=False)
    recommendation = Column(Text, nullable=False)
    ai_reasoning = Column(Text, nullable=True)
    status = Column(SAEnum(InterventionStatus), default=InterventionStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="interventions")
    alert = relationship("Alert", back_populates="interventions")
