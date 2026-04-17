"""Unit tests for course and instructor model constraints."""

from app.modules.courses.models import Course
from app.modules.instructors.models import Instructor


def test_course_column_defaults():
    table = Course.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["duration_minutes"].default.arg == 60
    assert cols["price"].default.arg == 0.0
    assert cols["is_active"].default.arg is True


def test_course_create_schema_defaults():
    from app.modules.courses.schemas import CourseCreate
    c = CourseCreate(title="Test Course")
    assert c.title == "Test Course"
    assert c.duration_minutes == 60
    assert c.price == 0.0


def test_course_create_with_price():
    from app.modules.courses.schemas import CourseCreate
    c = CourseCreate(title="Paid Course", price=99.99)
    assert c.price == 99.99


def test_instructor_column_defaults():
    table = Instructor.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["is_active"].default.arg is True
    assert cols["bio"].nullable is True


def test_instructor_create_schema():
    import uuid
    from app.modules.instructors.schemas import InstructorCreate
    inst = InstructorCreate(user_id=uuid.uuid4())
    assert inst.bio is None


def test_instructor_create_schema_with_bio():
    import uuid
    from app.modules.instructors.schemas import InstructorCreate
    inst = InstructorCreate(user_id=uuid.uuid4(), bio="Expert trainer")
    assert inst.bio == "Expert trainer"
