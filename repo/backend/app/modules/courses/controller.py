import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.exceptions import NotFoundError
from app.modules.courses.models import Course
from app.modules.courses.schemas import CourseCreate, CourseResponse, CourseUpdate

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("", response_model=list[CourseResponse])
async def list_courses(is_active: bool | None = None, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Course)
    if is_active is not None:
        q = q.where(Course.is_active == is_active)
    result = await db.execute(q.order_by(Course.title))
    return result.scalars().all()


@router.post("", response_model=CourseResponse, status_code=201)
async def create_course(body: CourseCreate, _=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    course = Course(**body.model_dump())
    db.add(course)
    await db.flush()
    await db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(course_id: uuid.UUID, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise NotFoundError("Course")
    return course


@router.patch("/{course_id}", response_model=CourseResponse)
async def update_course(course_id: uuid.UUID, body: CourseUpdate, _=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise NotFoundError("Course")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(course, k, v)
    await db.flush()
    return course


@router.delete("/{course_id}", status_code=204)
async def delete_course(course_id: uuid.UUID, _=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise NotFoundError("Course")
    course.is_active = False
    await db.flush()
