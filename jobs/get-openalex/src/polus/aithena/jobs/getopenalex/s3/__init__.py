"""S3 interface for the OpenAlex REST API."""

from .s3_types import SnapshotS3, S3Directory
from .__main__ import app

__all__ = ["SnapshotS3", "S3Directory", "app"]
