from pathlib import Path

from app.core.config import get_settings


def configured() -> bool:
    settings = get_settings()
    return bool(
        settings.s3_endpoint
        and settings.s3_bucket
        and settings.s3_access_key
        and settings.s3_secret_key
    )


def put_file(local_path: str, object_key: str) -> None:
    settings = get_settings()
    if not configured():
        return
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.s3_bucket)
    client.upload_file(
        local_path, settings.s3_bucket, object_key, ExtraArgs={"ContentType": "application/pdf"}
    )


def get_file(object_key: str) -> bytes:
    settings = get_settings()
    if not configured():
        path = Path(object_key)
        if not path.is_file():
            raise FileNotFoundError(object_key)
        return path.read_bytes()
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )
    return client.get_object(Bucket=settings.s3_bucket, Key=object_key)["Body"].read()


def object_exists(object_key: str) -> bool:
    """Return whether a previously exported object is still retrievable."""
    settings = get_settings()
    if not configured():
        return Path(object_key).is_file()
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )
    try:
        client.head_object(Bucket=settings.s3_bucket, Key=object_key)
    except (BotoCoreError, ClientError):
        return False
    return True
