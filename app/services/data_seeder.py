import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Student, Attendance, Assessment, AttendanceStatus, AssessmentType, RiskLevel

FIRST_NAMES = [
    "Ahmed", "Fatima", "Hassan", "Ayesha", "Bilal", "Zainab", "Omar", "Maryam",
    "Ali", "Sara", "Usman", "Hira", "Hamza", "Amna", "Ibrahim", "Khadija",
    "Zaid", "Sana", "Tahir", "Noor", "Saad", "Mahnoor", "Faisal", "Iqra",
    "Kashif", "Rabia", "Junaid", "Mehreen", "Arsalan", "Anam", "Shaheer",
    "Laiba", "Waqas", "Nimra", "Danish", "Bushra", "Naveed", "Sundas",
    "Kamran", "Alina", "Farhan", "Sadia", "Rizwan", "Huma", "Asim", "Tania",
    "Irfan", "Farah", "Nadeem", "Samia", "Adeel", "Lubna", "Shoaib", "Nadia",
    "Tariq", "Uzma", "Babar", "Rida", "Salman", "Areeba",
]

LAST_NAMES = [
    "Khan", "Ahmed", "Ali", "Malik", "Sheikh", "Hussain", "Butt", "Iqbal",
    "Raza", "Siddiqui", "Qureshi", "Shah", "Mirza", "Aslam", "Javed",
    "Rashid", "Anwar", "Farooq", "Chaudhry", "Rehman",
]

COURSES = [
    "Software Engineering", "Data Structures", "Database Systems",
    "Operating Systems", "Artificial Intelligence",
]

SECTIONS = ["A", "B", "C"]


def _make_student_profile():
    """Generate a random student personality to drive their data patterns."""
    profile = random.choices(
        ["excellent", "good", "average", "struggling", "at_risk"],
        weights=[15, 25, 30, 20, 10],
        k=1,
    )[0]
    return profile


def _attendance_probability(profile: str) -> float:
    """How likely this student is to show up on any given day."""
    return {
        "excellent": 0.95, "good": 0.88, "average": 0.78,
        "struggling": 0.62, "at_risk": 0.45,
    }[profile]


def _grade_range(profile: str) -> tuple[float, float]:
    """Score range (as fraction of max) for this profile."""
    return {
        "excellent": (0.82, 0.98), "good": (0.70, 0.88), "average": (0.55, 0.75),
        "struggling": (0.35, 0.60), "at_risk": (0.15, 0.45),
    }[profile]


def _late_probability(profile: str) -> float:
    """How likely submissions are to be late."""
    return {
        "excellent": 0.03, "good": 0.10, "average": 0.22,
        "struggling": 0.42, "at_risk": 0.65,
    }[profile]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _sample_student_signal() -> float:
    """Generate a latent student strength signal from a standard normal distribution."""
    return random.gauss(0.0, 1.0)


def _sample_gpa_target(signal: float) -> float:
    """Generate a GPA target from a normal distribution centered above the minimum threshold."""
    mean = 2.75 + (signal * 0.55)
    return round(_clamp(random.gauss(mean, 0.28), 0.0, 4.0), 2)


def _sample_attendance_target(signal: float) -> float:
    """Generate an attendance target from a normal distribution centered in the healthy range."""
    mean = 80.0 + (signal * 8.0)
    return round(_clamp(random.gauss(mean, 5.5), 0.0, 100.0), 1)


def _sample_late_target(signal: float) -> float:
    """Generate a late-submission target from a normal distribution."""
    mean = 18.0 - (signal * 6.0)
    return round(_clamp(random.gauss(mean, 4.5), 0.0, 100.0), 1)


def seed_database(db: Session, num_students: int = 60):
    """Generate synthetic student data with realistic patterns."""

    # wipe existing data
    for model in [Assessment, Attendance, Student]:
        db.query(model).delete()
    db.commit()

    # we also need to clear alerts and interventions
    from app.models import Alert, Intervention
    db.query(Intervention).delete()
    db.query(Alert).delete()
    db.commit()

    students = []
    used_names = set()

    for i in range(num_students):
        # avoid duplicate names
        while True:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            full_name = f"{first} {last}"
            if full_name not in used_names:
                used_names.add(full_name)
                break

        roll = f"23K-{random.randint(1000, 9999)}"
        email = f"{first.lower()}.{last.lower()}{random.randint(1,99)}@nu.edu.pk"
        section = random.choice(SECTIONS)
        semester = random.choice([3, 4, 5, 6])
        student_signal = _sample_student_signal()

        student = Student(
            name=full_name, email=email, roll_number=roll,
            section=section, semester=semester,
        )
        db.add(student)
        db.flush()  # get the ID

        # generate attendance for the last 30 days
        attend_target = _sample_attendance_target(student_signal)
        attend_prob = attend_target / 100.0
        today = datetime.now().date()
        present_count = 0
        total_count = 0

        for day_offset in range(30):
            date = today - timedelta(days=day_offset)
            if date.weekday() >= 5:  # skip weekends
                continue
            for course in COURSES:
                total_count += 1
                roll_val = random.random()
                if roll_val < attend_prob:
                    status = AttendanceStatus.PRESENT
                    present_count += 1
                elif roll_val < attend_prob + 0.08:
                    status = AttendanceStatus.LATE
                    present_count += 1  # late still counts
                else:
                    status = AttendanceStatus.ABSENT

                db.add(Attendance(
                    student_id=student.id, date=date,
                    status=status, course=course,
                ))

        # calculate attendance percentage
        student.attendance_percentage = round(
            (present_count / max(total_count, 1)) * 100, 1
        )

        # generate assessments
        target_gpa = _sample_gpa_target(student_signal)
        target_frac = target_gpa / 4.0
        late_target = _sample_late_target(student_signal)
        late_prob = late_target / 100.0
        total_weighted = 0
        total_weight = 0

        for course in COURSES:
            # 3 quizzes, 2 assignments, 1 exam per course
            assessments_config = [
                ("quiz", 10, 3), ("assignment", 50, 2), ("exam", 100, 1),
            ]
            for a_type, max_score, count in assessments_config:
                for j in range(count):
                    score_frac = _clamp(random.gauss(target_frac, 0.10), 0.0, 1.0)
                    score = round(score_frac * max_score, 1)
                    due = today - timedelta(days=random.randint(1, 28))
                    is_late = random.random() < late_prob
                    submitted = due + timedelta(days=random.randint(1, 3)) if is_late else due

                    db.add(Assessment(
                        student_id=student.id,
                        type=AssessmentType(a_type),
                        course=course,
                        title=f"{course} {a_type.title()} {j+1}",
                        score=score, max_score=max_score,
                        due_date=datetime.combine(due, datetime.min.time()),
                        submitted_at=datetime.combine(submitted, datetime.min.time()),
                        is_late=is_late,
                    ))

                    # weight exams more for GPA approximation
                    weight = {"quiz": 1, "assignment": 2, "exam": 4}[a_type]
                    total_weighted += score_frac * weight
                    total_weight += weight

        # approximate GPA on 4.0 scale and nudge it toward the sampled target
        avg_frac = total_weighted / max(total_weight, 1)
        blended_frac = (avg_frac * 0.35) + (target_frac * 0.65)
        student.overall_gpa = round(_clamp(blended_frac * 4.0, 0.0, 4.0), 2)

        students.append(student)

    db.commit()
    return len(students)
