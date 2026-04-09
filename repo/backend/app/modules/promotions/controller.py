import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.exceptions import NotFoundError
from app.modules.checkout.schemas import BestOfferResponse, CartCreate
from app.modules.checkout.service import CheckoutService
from app.modules.promotions.models import Promotion
from app.modules.promotions.schemas import PromotionCreate, PromotionResponse, PromotionUpdate

router = APIRouter(prefix="/promotions", tags=["Promotions"])


@router.post("/preview", response_model=BestOfferResponse)
async def preview_promotions(body: CartCreate, _=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    """Dry-run: compute which promotions would apply to a given cart without persisting anything."""
    return await CheckoutService(db).get_best_offer(body)


@router.get("", response_model=list[PromotionResponse])
async def list_promotions(is_active: bool | None = None, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Promotion)
    if is_active is not None:
        q = q.where(Promotion.is_active == is_active)
    result = await db.execute(q.order_by(Promotion.name))
    return result.scalars().all()


@router.post("", response_model=PromotionResponse, status_code=201)
async def create_promotion(body: PromotionCreate, current_user=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    promo = Promotion(**body.model_dump())
    db.add(promo)
    await db.flush()
    await db.refresh(promo)
    await log_audit(db, str(current_user.id), "promotion", str(promo.id), "create", new_value=body.model_dump(mode="json"))
    return promo


@router.get("/{promo_id}", response_model=PromotionResponse)
async def get_promotion(promo_id: uuid.UUID, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Promotion).where(Promotion.id == promo_id))
    p = result.scalar_one_or_none()
    if not p:
        raise NotFoundError("Promotion")
    return p


@router.patch("/{promo_id}", response_model=PromotionResponse)
async def update_promotion(promo_id: uuid.UUID, body: PromotionUpdate, current_user=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Promotion).where(Promotion.id == promo_id))
    p = result.scalar_one_or_none()
    if not p:
        raise NotFoundError("Promotion")
    old = {k: getattr(p, k) for k in body.model_dump(exclude_none=True)}
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    await db.flush()
    await log_audit(db, str(current_user.id), "promotion", str(p.id), "update",
                    old_value={k: str(v) for k, v in old.items()},
                    new_value=body.model_dump(exclude_none=True, mode="json"))
    return p


@router.delete("/{promo_id}", status_code=204)
async def delete_promotion(promo_id: uuid.UUID, current_user=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Promotion).where(Promotion.id == promo_id))
    p = result.scalar_one_or_none()
    if not p:
        raise NotFoundError("Promotion")
    p.is_active = False
    await db.flush()
    await log_audit(db, str(current_user.id), "promotion", str(p.id), "delete")
