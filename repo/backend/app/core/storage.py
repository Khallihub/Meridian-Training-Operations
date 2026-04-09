"""MinIO object storage client helpers."""

from datetime import timedelta
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
    return _client


def ensure_bucket_exists(bucket: str) -> None:
    client = get_minio_client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_object(bucket: str, object_key: str, data: bytes, content_type: str = "video/mp4") -> None:
    client = get_minio_client()
    ensure_bucket_exists(bucket)
    client.put_object(bucket, object_key, BytesIO(data), length=len(data), content_type=content_type)


def get_presigned_download_url(bucket: str, object_key: str) -> str:
    client = get_minio_client()
    url = client.presigned_get_object(
        bucket,
        object_key,
        expires=timedelta(seconds=settings.PRESIGNED_URL_EXPIRE_SECONDS),
    )
    # Rewrite the internal MinIO hostname to the public-facing endpoint so
    # browsers can reach the URL (minio:9000 is only resolvable inside Docker).
    public = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
    if public != settings.MINIO_ENDPOINT:
        scheme = "https" if settings.MINIO_USE_SSL else "http"
        url = url.replace(f"{scheme}://{settings.MINIO_ENDPOINT}", f"{scheme}://{public}", 1)
    return url


def get_presigned_upload_url(bucket: str, object_key: str) -> str:
    client = get_minio_client()
    ensure_bucket_exists(bucket)
    return client.presigned_put_object(
        bucket,
        object_key,
        expires=timedelta(seconds=settings.PRESIGNED_URL_EXPIRE_SECONDS),
    )


def stat_object(bucket: str, object_key: str):
    """Return object stat (has .size and .content_type)."""
    client = get_minio_client()
    return client.stat_object(bucket, object_key)


def get_object_chunks(bucket: str, object_key: str, offset: int = 0, length: int | None = None):
    """Generator that yields raw bytes from MinIO, supporting byte-range reads."""
    client = get_minio_client()
    kwargs: dict = {}
    if offset:
        kwargs["offset"] = offset
    if length is not None:
        kwargs["length"] = length
    response = client.get_object(bucket, object_key, **kwargs)
    try:
        for chunk in response.stream(amt=64 * 1024):
            yield chunk
    finally:
        response.close()
        response.release_conn()


def delete_object(bucket: str, object_key: str) -> None:
    client = get_minio_client()
    try:
        client.remove_object(bucket, object_key)
    except S3Error:
        pass
