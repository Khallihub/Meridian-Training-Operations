import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.pagination import Page, PageMeta
from app.modules.checkout.schemas import BestOfferResponse, CartCreate, OrderResponse
from app.modules.checkout.service import CheckoutService

router = APIRouter(tags=["Checkout & Orders"])


@router.post("/checkout/cart", response_model=OrderResponse, status_code=201)
async def create_cart(
    body: CartCreate,
    current_user=Depends(require_roles("learner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    return await CheckoutService(db).create_cart(body, current_user.id)


@router.post("/checkout/best-offer", response_model=BestOfferResponse)
async def get_best_offer(
    body: CartCreate,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CheckoutService(db).get_best_offer(body)


@router.get("/orders", response_model=Page[OrderResponse])
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles("admin", "finance", "learner")),
    db: AsyncSession = Depends(get_db),
):
    learner_id = current_user.id if current_user.role == "learner" else None
    items, total = await CheckoutService(db).list_orders(learner_id, page, page_size)
    return Page(items=items, meta=PageMeta(total_count=total, page=page, page_size=page_size, has_next=(page * page_size < total)))


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    current_user=Depends(require_roles("admin", "finance", "learner")),
    db: AsyncSession = Depends(get_db),
):
    return await CheckoutService(db).get_order(order_id, caller_id=str(current_user.id), caller_role=current_user.role)


@router.patch("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: uuid.UUID,
    current_user=Depends(require_roles("admin", "finance", "learner")),
    db: AsyncSession = Depends(get_db),
):
    return await CheckoutService(db).cancel_order(order_id, caller_id=str(current_user.id), caller_role=current_user.role)
