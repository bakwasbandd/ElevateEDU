import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    APP_NAME = "ElevateEDU"
    APP_VERSION = "1.0.0"
    DATABASE_URL = "sqlite:///./elevate_edu.db"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # risk thresholds — tweak from settings page
    ATTENDANCE_RISK_THRESHOLD = 75.0
    GPA_RISK_THRESHOLD = 2.0
    LATE_SUBMISSION_THRESHOLD = 30.0  # percentage

    # risk weights for composite score
    ATTENDANCE_WEIGHT = 0.30
    ACADEMIC_WEIGHT = 0.60
    SUBMISSION_WEIGHT = 0.10

    # AI strategy: "mock", "cloud", or "local"
    AI_STRATEGY = os.getenv("AI_STRATEGY", "mock")

    # cloud LLM config
    CLOUD_LLM_API_KEY = os.getenv("GROQ_API_KEY", os.getenv("XAI_API_KEY", os.getenv("LLM_API_KEY", "")))
    CLOUD_LLM_MODEL = os.getenv("GROQ_MODEL", os.getenv("XAI_MODEL", os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")))

    # local LLM config (Ollama)
    LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:11434")
    LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.2:3b")

    # data generation
    NUM_STUDENTS = 60
    NUM_COURSES = 5
    ATTENDANCE_DAYS = 30


config = Config()
