# ElevateEDU

AI-powered student risk monitoring and intervention system. Built as a Software Engineering project demonstrating design pattern implementation (SE Objective 4).

## What It Does

Monitors student academic data — attendance, quiz scores, assignment submissions, and performance trends — to automatically identify at-risk students and recommend targeted interventions. Combines predictive analytics with explainable AI to surface actionable insights for educators.

## Design Patterns Used

| Pattern | Where | Why |
|---------|-------|-----|
| **Observer** | `app/patterns/observer.py` | StudentDataMonitor watches for threshold breaches and notifies AttendanceObserver, GradeObserver, SubmissionObserver |
| **Strategy** | `app/patterns/strategy.py` | Swappable AI engines (Mock/Cloud LLM/Local LLM) behind a common interface — change at runtime from settings |
| **Factory** | `app/patterns/factory.py` | Creates typed intervention reports (Attendance, Academic, Submission) based on risk classification |
| **Singleton + MVC** | `app/patterns/singleton.py` + overall architecture | Single MonitoringEngine instance, clean Model-View-Controller separation |

## Before/After Refactoring

See `before/monolithic_app.py` for the deliberately messy monolithic version. Compare with the `app/` directory to see how design patterns improve maintainability, extensibility, and testability.

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Jinja2 + Vanilla CSS/JS
- **Database**: SQLite via SQLAlchemy
- **AI**: Swappable — Gemini API / Ollama / Mock rule-based
- **Charts**: Chart.js

## Setup

```bash
# install dependencies
pip install -r requirements.txt

# run the server
python run.py
```

Open http://127.0.0.1:8000 in your browser.

On first run, the system auto-generates 60 synthetic students with realistic academic profiles.

## Using the System

1. **Dashboard** — overview of risk distribution and recent alerts
2. **Students** — browse, filter, and search students; click any student for detailed analysis
3. **Alerts** — click "Run Scan" to trigger the Observer pipeline and generate risk alerts
4. **Reports** — class-wide analytics with GPA/attendance distributions
5. **Settings** — swap AI strategy (Mock/Cloud/Local), adjust risk thresholds, regenerate data

## AI Strategy Configuration

Set the `AI_STRATEGY` environment variable or use the Settings page:

- `mock` — Rule-based analysis, no API key needed (default)
- `cloud` — Cloud LLM (set `LLM_API_KEY` env var)
- `local` — Ollama on localhost:11434

## Team

- 3 members
- FAST-NUCES Karachi, Spring 2026
