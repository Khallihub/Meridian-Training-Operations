import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.pagination import Page, PageMeta
from app.modules.payments.schemas import (
    PaymentCallbackPayload, PaymentResponse,
    ReconciliationExportResponse, RefundCreate, RefundResponse,
)
from app.modules.payments.service import PaymentService

router = APIRouter(tags=["Payments & Refunds"])


@router.get("/payments", response_model=Page[PaymentResponse])
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _=Depends(require_roles("admin", "finance")),
    db: AsyncSession = Depends(get_db),
):
    items, total = await PaymentService(db).list_payments(page, page_size)
    return Page(items=items, meta=PageMeta(total_count=total, page=page, page_size=page_size, has_next=(page * page_size < total)))


@router.post("/payments/callback", response_model=PaymentResponse)
async def payment_callback(body: PaymentCallbackPayload, db: AsyncSession = Depends(get_db)):
    """LAN terminal callback — no auth required (verified by HMAC signature)."""
    return await PaymentService(db).handle_callback(body)


@router.post("/payments/{order_id}/simulate", response_model=PaymentResponse)
async def simulate_payment(order_id: uuid.UUID, _=Depends(require_roles("admin", "finance", "learner")), db: AsyncSession = Depends(get_db)):
    """Simulate a terminal payment callback — restricted to admin and finance roles."""
    return await PaymentService(db).simulate_payment(order_id)


@router.get("/payments/{order_id}", response_model=PaymentResponse)
async def get_payment(order_id: uuid.UUID, _=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    return await PaymentService(db).get_payment(order_id)


@router.get("/refunds", response_model=list[RefundResponse])
async def list_refunds(
    status: str | None = None,
    _=Depends(require_roles("admin", "finance")),
    db: AsyncSession = Depends(get_db),
):
    return await PaymentService(db).list_refunds(status)


@router.post("/refunds", response_model=RefundResponse, status_code=201)
async def create_refund(body: RefundCreate, current_user=Depends(require_roles("admin", "finance", "learner")), db: AsyncSession = Depends(get_db)):
    return await PaymentService(db).create_refund(body, current_user.id)


@router.get("/refunds/{refund_id}", response_model=RefundResponse)
async def get_refund(refund_id: uuid.UUID, _=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    return await PaymentService(db).get_refund(refund_id)


@router.patch("/refunds/{refund_id}/review", response_model=RefundResponse)
async def review_refund(refund_id: uuid.UUID, current_user=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    """Acknowledge a refund request and move it to pending_review (requested → pending_review)."""
    return await PaymentService(db).review_refund(refund_id, str(current_user.id))


@router.patch("/refunds/{refund_id}/approve", response_model=RefundResponse)
async def approve_refund(refund_id: uuid.UUID, current_user=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    """Approve a refund under review (pending_review → approved)."""
    return await PaymentService(db).approve_refund(refund_id, str(current_user.id))


@router.patch("/refunds/{refund_id}/reject", response_model=RefundResponse)
async def reject_refund(refund_id: uuid.UUID, current_user=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    """Reject a refund under review (pending_review → rejected)."""
    return await PaymentService(db).reject_refund(refund_id, str(current_user.id))


@router.patch("/refunds/{refund_id}/process", response_model=RefundResponse)
async def process_refund(refund_id: uuid.UUID, current_user=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    """Move approved refund to processing state (approved → processing)."""
    return await PaymentService(db).process_refund(refund_id, str(current_user.id))


@router.patch("/refunds/{refund_id}/complete", response_model=RefundResponse)
async def complete_refund(refund_id: uuid.UUID, current_user=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    """Complete a refund in processing (processing → completed)."""
    return await PaymentService(db).complete_refund(refund_id, str(current_user.id))


@router.post("/reconciliation/export", response_model=ReconciliationExportResponse)
async def trigger_reconciliation(
    export_date: str | None = None,
    _=Depends(require_roles("admin", "finance")),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date
    d = date.fromisoformat(export_date) if export_date else None
    return await PaymentService(db).generate_reconciliation_export(d)


@router.get("/reconciliation/export", response_model=ReconciliationExportResponse)
async def trigger_reconciliation_get(
    export_date: str | None = None,
    _=Depends(require_roles("admin", "finance")),
    db: AsyncSession = Depends(get_db),
):
    """GET alias for frontend compatibility."""
    from datetime import date
    d = date.fromisoformat(export_date) if export_date else None
    return await PaymentService(db).generate_reconciliation_export(d)


@router.get("/reconciliation/exports", response_model=list[ReconciliationExportResponse])
async def list_exports(_=Depends(require_roles("admin", "finance")), db: AsyncSession = Depends(get_db)):
    return await PaymentService(db).list_exports()


@router.get("/reconciliation/exports/{export_id}/download")
async def download_export(
    export_id: uuid.UUID,
    _=Depends(require_roles("admin", "finance")),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import RedirectResponse
    from app.core.storage import get_presigned_download_url
    export = await PaymentService(db).get_export(export_id)
    # Reconciliation files are stored locally; serve via presigned URL if on MinIO,
    # or fall back to a direct file response for local paths
    import os
    if os.path.exists(export.file_path):
        from fastapi.responses import FileResponse
        return FileResponse(
            export.file_path,
            media_type="text/csv",
            filename=os.path.basename(export.file_path),
        )
    # MinIO path
    from app.core.config import settings
    url = get_presigned_download_url(settings.MINIO_BUCKET_RECORDINGS, export.file_path)
    return RedirectResponse(url=url)
