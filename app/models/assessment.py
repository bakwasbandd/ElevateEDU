from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AssessmentType(str, enum.Enum):
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    EXAM = "exam"


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    type = Column(SAEnum(AssessmentType), nullable=False)
    course = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=False)
    is_late = Column(Boolean, default=False)

    student = relationship("Student", back_populates="assessments")

    @property
    def percentage(self):
        if self.max_score == 0:
            return 0
        return round((self.score / self.max_score) * 100, 1)
