import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.exceptions import NotFoundError
from app.modules.instructors.models import Instructor
from app.modules.instructors.schemas import InstructorCreate, InstructorResponse, InstructorUpdate

router = APIRouter(prefix="/instructors", tags=["Instructors"])


def _with_user(q):
    return q.options(selectinload(Instructor.user))


def _to_response(inst: Instructor) -> InstructorResponse:
    return InstructorResponse(
        id=inst.id,
        user_id=inst.user_id,
        username=inst.user.username,
        bio=inst.bio,
        is_active=inst.is_active,
        created_at=inst.created_at,
    )


@router.get("", response_model=list[InstructorResponse])
async def list_instructors(is_active: bool | None = None, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = _with_user(select(Instructor))
    if is_active is not None:
        q = q.where(Instructor.is_active == is_active)
    result = await db.execute(q)
    return [_to_response(i) for i in result.scalars().all()]


@router.post("", response_model=InstructorResponse, status_code=201)
async def create_instructor(body: InstructorCreate, _=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    inst = Instructor(**body.model_dump())
    db.add(inst)
    await db.flush()
    await db.refresh(inst)
    result = await db.execute(_with_user(select(Instructor).where(Instructor.id == inst.id)))
    return _to_response(result.scalar_one())


@router.get("/{instructor_id}", response_model=InstructorResponse)
async def get_instructor(instructor_id: uuid.UUID, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(_with_user(select(Instructor).where(Instructor.id == instructor_id)))
    inst = result.scalar_one_or_none()
    if not inst:
        raise NotFoundError("Instructor")
    return _to_response(inst)


@router.patch("/{instructor_id}", response_model=InstructorResponse)
async def update_instructor(instructor_id: uuid.UUID, body: InstructorUpdate, _=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(_with_user(select(Instructor).where(Instructor.id == instructor_id)))
    inst = result.scalar_one_or_none()
    if not inst:
        raise NotFoundError("Instructor")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(inst, k, v)
    await db.flush()
    return _to_response(inst)


@router.delete("/{instructor_id}", status_code=204)
async def delete_instructor(instructor_id: uuid.UUID, _=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Instructor).where(Instructor.id == instructor_id))
    inst = result.scalar_one_or_none()
    if not inst:
        raise NotFoundError("Instructor")
    inst.is_active = False
    await db.flush()
