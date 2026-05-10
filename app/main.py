from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from app.database import init_db, SessionLocal
from app.services.data_seeder import seed_database
from app.controllers import dashboard, students, alerts, reports, settings

app = FastAPI(title="ElevateEDU", version="1.0.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# wire up all the routers
app.include_router(dashboard.router)
app.include_router(students.router)
app.include_router(alerts.router)
app.include_router(reports.router)
app.include_router(settings.router)


@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.on_event("startup")
def on_startup():
    init_db()
    # seed data if the database is empty
    db = SessionLocal()
    try:
        from app.models import Student
        if db.query(Student).count() == 0:
            seed_database(db)
    finally:
        db.close()
