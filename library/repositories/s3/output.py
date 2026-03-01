"""S3 implementation of CloudOutputRepository.

Stores setlist outputs (markdown, PDF) and chord content in an S3-compatible
bucket, organized by org_id for multi-tenant deployments.

Key layout:
    orgs/{org_id}/setlists/{event_type}/{date}_{label}.{ext}
    orgs/{org_id}/songs/{song_id}/chords.md

Requires boto3 (install with: pip install boto3).
"""

from __future__ import annotations

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None  # type: ignore[assignment]
    ClientError = None  # type: ignore[assignment,misc]

_PRESIGNED_URL_EXPIRY = 3600  # 1 hour


class S3OutputRepository:
    """CloudOutputRepository backed by S3-compatible object storage.

    Args:
        bucket: S3 bucket name.
        org_id: Organization identifier used as the key prefix.
        s3_client: Optional pre-configured boto3 S3 client. If *None*,
            a new client is created via ``boto3.client("s3", ...)``.
        endpoint_url: Optional custom endpoint for S3-compatible services
            (e.g. MinIO, R2). Only used when *s3_client* is None.
    """

    def __init__(
        self,
        bucket: str,
        org_id: str,
        s3_client=None,
        endpoint_url: str | None = None,
    ) -> None:
        if s3_client is not None:
            self._client = s3_client
        else:
            if boto3 is None:
                raise ImportError(
                    "S3 output repository requires boto3. "
                    "Install with: pip install boto3"
                )
            self._client = boto3.client("s3", endpoint_url=endpoint_url)

        self._bucket = bucket
        self._org_id = org_id

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    def _build_setlist_key(
        self,
        date: str,
        label: str = "",
        event_type: str = "",
        extension: str = ".md",
    ) -> str:
        """Build an S3 object key for a setlist output.

        Pattern: orgs/{org_id}/setlists/{event_type}/{stem}{extension}

        When *event_type* is empty the literal ``"default"`` is used.
        When *label* is empty the stem is just ``{date}``, otherwise
        ``{date}_{label}``.
        """
        et = event_type if event_type else "default"
        stem = f"{date}_{label}" if label else date
        return f"orgs/{self._org_id}/setlists/{et}/{stem}{extension}"

    def _build_chord_key(self, song_id: str) -> str:
        """Build an S3 object key for chord content.

        Pattern: orgs/{org_id}/songs/{song_id}/chords.md
        """
        return f"orgs/{self._org_id}/songs/{song_id}/chords.md"

    def _build_setlist_prefix(
        self,
        date: str,
        label: str = "",
        event_type: str = "",
    ) -> str:
        """Build the common prefix for listing setlist objects.

        Returns a prefix that matches both .md and .pdf keys for the
        given date/label/event_type combination.
        """
        et = event_type if event_type else "default"
        stem = f"{date}_{label}" if label else date
        return f"orgs/{self._org_id}/setlists/{et}/{stem}"

    # ------------------------------------------------------------------
    # Presigned URL helper
    # ------------------------------------------------------------------

    def _presigned_url_or_none(self, key: str) -> str | None:
        """Generate a presigned GET URL, or return None if key is missing."""
        try:
            # HEAD the object first to confirm it exists.
            self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                return None
            raise

        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=_PRESIGNED_URL_EXPIRY,
        )

    # ------------------------------------------------------------------
    # CloudOutputRepository interface
    # ------------------------------------------------------------------

    def save_markdown(
        self,
        date: str,
        content: str,
        label: str = "",
        event_type: str = "",
    ) -> str:
        """Save setlist markdown to S3.

        Returns:
            The S3 key of the stored object.
        """
        key = self._build_setlist_key(date, label, event_type, extension=".md")
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="text/markdown; charset=utf-8",
        )
        return key

    def save_pdf_bytes(
        self,
        date: str,
        pdf_bytes: bytes,
        label: str = "",
        event_type: str = "",
    ) -> str:
        """Save PDF bytes to S3.

        Returns:
            The S3 key of the stored object.
        """
        key = self._build_setlist_key(date, label, event_type, extension=".pdf")
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
        return key

    def get_markdown_url(
        self,
        date: str,
        label: str = "",
        event_type: str = "",
    ) -> str | None:
        """Get a presigned URL for the markdown file, or None if missing."""
        key = self._build_setlist_key(date, label, event_type, extension=".md")
        return self._presigned_url_or_none(key)

    def get_pdf_url(
        self,
        date: str,
        label: str = "",
        event_type: str = "",
    ) -> str | None:
        """Get a presigned URL for the PDF file, or None if missing."""
        key = self._build_setlist_key(date, label, event_type, extension=".pdf")
        return self._presigned_url_or_none(key)

    def save_chord_content(self, song_id: str, content: str) -> str:
        """Save chord content to S3.

        Returns:
            The S3 key of the stored object.
        """
        key = self._build_chord_key(song_id)
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="text/markdown; charset=utf-8",
        )
        return key

    def get_chord_content(self, song_id: str) -> str | None:
        """Get chord content from S3, or None if not found."""
        key = self._build_chord_key(song_id)
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read().decode("utf-8")
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                return None
            raise

    def delete_outputs(
        self,
        date: str,
        label: str = "",
        event_type: str = "",
    ) -> int:
        """Delete all output objects (markdown + PDF) for a setlist.

        Uses ``list_objects_v2`` with a prefix filter, then
        ``delete_objects`` in a single batch request.

        Returns:
            Number of objects deleted.
        """
        prefix = self._build_setlist_prefix(date, label, event_type)

        # Collect all keys matching the prefix.
        keys_to_delete: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys_to_delete.append(obj["Key"])

        if not keys_to_delete:
            return 0

        # Batch delete (S3 supports up to 1000 per request; fine for our use).
        self._client.delete_objects(
            Bucket=self._bucket,
            Delete={"Objects": [{"Key": k} for k in keys_to_delete]},
        )
        return len(keys_to_delete)
