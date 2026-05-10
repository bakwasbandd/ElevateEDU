from sqlalchemy import Column, Integer, String, Float, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class RiskLevel(str, enum.Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    roll_number = Column(String(20), unique=True, nullable=False)
    section = Column(String(5), nullable=False)
    semester = Column(Integer, nullable=False)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.NONE)
    overall_gpa = Column(Float, default=0.0)
    attendance_percentage = Column(Float, default=100.0)

    attendance_records = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="student", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="student", cascade="all, delete-orphan")
    interventions = relationship("Intervention", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student {self.roll_number}: {self.name}>"
