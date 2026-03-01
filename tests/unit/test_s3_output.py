"""Unit tests for the S3OutputRepository.

All tests inject a MagicMock as the s3_client so no real AWS calls are made.
Requires boto3/botocore (install via: uv sync --group saas).
"""

from unittest.mock import MagicMock, call, patch

import pytest

boto3 = pytest.importorskip("boto3", reason="boto3 not installed (uv sync --group saas)")
from botocore.exceptions import ClientError  # noqa: E402

from library.repositories.s3 import S3OutputRepository  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BUCKET = "test-bucket"
ORG_ID = "org-abc123"


@pytest.fixture()
def s3_client() -> MagicMock:
    """Pre-configured mock S3 client."""
    return MagicMock()


@pytest.fixture()
def repo(s3_client: MagicMock) -> S3OutputRepository:
    """S3OutputRepository wired to the mock client."""
    return S3OutputRepository(
        bucket=BUCKET,
        org_id=ORG_ID,
        s3_client=s3_client,
    )


def _no_such_key_error() -> ClientError:
    """Create a ClientError that mimics S3 NoSuchKey."""
    return ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
        "HeadObject",
    )


def _404_error() -> ClientError:
    """Create a ClientError with a 404 code."""
    return ClientError(
        {"Error": {"Code": "404", "Message": "Not found"}},
        "HeadObject",
    )


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------


class TestBuildSetlistKey:
    """Verify _build_setlist_key produces the expected S3 keys."""

    def test_default_event_type_no_label(self, repo: S3OutputRepository):
        key = repo._build_setlist_key("2026-03-01")
        assert key == f"orgs/{ORG_ID}/setlists/default/2026-03-01.md"

    def test_default_event_type_with_label(self, repo: S3OutputRepository):
        key = repo._build_setlist_key("2026-03-01", label="evening")
        assert key == f"orgs/{ORG_ID}/setlists/default/2026-03-01_evening.md"

    def test_custom_event_type_no_label(self, repo: S3OutputRepository):
        key = repo._build_setlist_key("2026-03-01", event_type="youth")
        assert key == f"orgs/{ORG_ID}/setlists/youth/2026-03-01.md"

    def test_custom_event_type_with_label(self, repo: S3OutputRepository):
        key = repo._build_setlist_key("2026-03-01", label="night", event_type="youth")
        assert key == f"orgs/{ORG_ID}/setlists/youth/2026-03-01_night.md"

    def test_pdf_extension(self, repo: S3OutputRepository):
        key = repo._build_setlist_key("2026-03-01", extension=".pdf")
        assert key.endswith(".pdf")

    def test_empty_event_type_uses_default(self, repo: S3OutputRepository):
        key = repo._build_setlist_key("2026-03-01", event_type="")
        assert "/default/" in key


class TestBuildChordKey:
    """Verify _build_chord_key produces the expected S3 keys."""

    def test_chord_key(self, repo: S3OutputRepository):
        key = repo._build_chord_key("song-uuid-42")
        assert key == f"orgs/{ORG_ID}/songs/song-uuid-42/chords.md"


# ---------------------------------------------------------------------------
# save_markdown
# ---------------------------------------------------------------------------


class TestSaveMarkdown:
    def test_returns_key_and_calls_put_object(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        content = "# Setlist\n\nSong A, Song B"
        key = repo.save_markdown("2026-03-01", content)

        expected_key = f"orgs/{ORG_ID}/setlists/default/2026-03-01.md"
        assert key == expected_key

        s3_client.put_object.assert_called_once_with(
            Bucket=BUCKET,
            Key=expected_key,
            Body=content.encode("utf-8"),
            ContentType="text/markdown; charset=utf-8",
        )

    def test_with_label_and_event_type(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        key = repo.save_markdown(
            "2026-03-01", "content", label="evening", event_type="youth"
        )

        expected_key = f"orgs/{ORG_ID}/setlists/youth/2026-03-01_evening.md"
        assert key == expected_key
        s3_client.put_object.assert_called_once()


# ---------------------------------------------------------------------------
# save_pdf_bytes
# ---------------------------------------------------------------------------


class TestSavePdfBytes:
    def test_returns_key_and_calls_put_object(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        pdf = b"%PDF-1.4 fake content"
        key = repo.save_pdf_bytes("2026-03-01", pdf)

        expected_key = f"orgs/{ORG_ID}/setlists/default/2026-03-01.pdf"
        assert key == expected_key

        s3_client.put_object.assert_called_once_with(
            Bucket=BUCKET,
            Key=expected_key,
            Body=pdf,
            ContentType="application/pdf",
        )

    def test_with_label(self, repo: S3OutputRepository, s3_client: MagicMock):
        key = repo.save_pdf_bytes("2026-03-01", b"pdf", label="morning")

        expected_key = f"orgs/{ORG_ID}/setlists/default/2026-03-01_morning.pdf"
        assert key == expected_key


# ---------------------------------------------------------------------------
# get_markdown_url / get_pdf_url
# ---------------------------------------------------------------------------


class TestGetMarkdownUrl:
    def test_returns_presigned_url_when_object_exists(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        expected_url = "https://s3.amazonaws.com/signed-url"
        s3_client.generate_presigned_url.return_value = expected_url

        url = repo.get_markdown_url("2026-03-01")

        assert url == expected_url

        # head_object should have been called to verify existence
        expected_key = f"orgs/{ORG_ID}/setlists/default/2026-03-01.md"
        s3_client.head_object.assert_called_once_with(
            Bucket=BUCKET, Key=expected_key
        )
        s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": BUCKET, "Key": expected_key},
            ExpiresIn=3600,
        )

    def test_returns_none_when_object_missing_nosuchkey(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        s3_client.head_object.side_effect = _no_such_key_error()

        url = repo.get_markdown_url("2026-03-01")

        assert url is None
        s3_client.generate_presigned_url.assert_not_called()

    def test_returns_none_when_object_missing_404(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        s3_client.head_object.side_effect = _404_error()

        url = repo.get_markdown_url("2026-03-01")

        assert url is None

    def test_reraises_unexpected_client_error(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}},
            "HeadObject",
        )
        s3_client.head_object.side_effect = error

        with pytest.raises(ClientError):
            repo.get_markdown_url("2026-03-01")


class TestGetPdfUrl:
    def test_returns_presigned_url_when_object_exists(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        expected_url = "https://s3.amazonaws.com/signed-pdf-url"
        s3_client.generate_presigned_url.return_value = expected_url

        url = repo.get_pdf_url("2026-03-01", label="evening", event_type="youth")

        assert url == expected_url

        expected_key = f"orgs/{ORG_ID}/setlists/youth/2026-03-01_evening.pdf"
        s3_client.head_object.assert_called_once_with(
            Bucket=BUCKET, Key=expected_key
        )

    def test_returns_none_when_not_found(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        s3_client.head_object.side_effect = _no_such_key_error()

        url = repo.get_pdf_url("2026-03-01")

        assert url is None


# ---------------------------------------------------------------------------
# save_chord_content / get_chord_content
# ---------------------------------------------------------------------------


class TestSaveChordContent:
    def test_returns_key_and_calls_put_object(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        content = "### Oceanos (G)\n\nG       D\nLyrics..."
        key = repo.save_chord_content("song-uuid-42", content)

        expected_key = f"orgs/{ORG_ID}/songs/song-uuid-42/chords.md"
        assert key == expected_key

        s3_client.put_object.assert_called_once_with(
            Bucket=BUCKET,
            Key=expected_key,
            Body=content.encode("utf-8"),
            ContentType="text/markdown; charset=utf-8",
        )


class TestGetChordContent:
    def test_returns_decoded_content(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        body_mock = MagicMock()
        body_mock.read.return_value = b"### Oceanos (G)\n\nG       D\nLyrics..."
        s3_client.get_object.return_value = {"Body": body_mock}

        content = repo.get_chord_content("song-uuid-42")

        assert content == "### Oceanos (G)\n\nG       D\nLyrics..."
        expected_key = f"orgs/{ORG_ID}/songs/song-uuid-42/chords.md"
        s3_client.get_object.assert_called_once_with(
            Bucket=BUCKET, Key=expected_key
        )

    def test_returns_none_when_not_found(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        s3_client.get_object.side_effect = _no_such_key_error()

        content = repo.get_chord_content("missing-song")

        assert content is None

    def test_returns_none_on_404(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        s3_client.get_object.side_effect = _404_error()

        content = repo.get_chord_content("missing-song")

        assert content is None

    def test_reraises_unexpected_error(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}},
            "GetObject",
        )
        s3_client.get_object.side_effect = error

        with pytest.raises(ClientError):
            repo.get_chord_content("some-song")


# ---------------------------------------------------------------------------
# delete_outputs
# ---------------------------------------------------------------------------


class TestDeleteOutputs:
    def test_deletes_matching_objects_and_returns_count(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        prefix = f"orgs/{ORG_ID}/setlists/default/2026-03-01"

        # Simulate paginator returning two objects (md + pdf)
        page = {
            "Contents": [
                {"Key": f"{prefix}.md"},
                {"Key": f"{prefix}.pdf"},
            ]
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [page]
        s3_client.get_paginator.return_value = mock_paginator

        count = repo.delete_outputs("2026-03-01")

        assert count == 2
        s3_client.get_paginator.assert_called_once_with("list_objects_v2")
        mock_paginator.paginate.assert_called_once_with(
            Bucket=BUCKET, Prefix=prefix
        )
        s3_client.delete_objects.assert_called_once_with(
            Bucket=BUCKET,
            Delete={
                "Objects": [
                    {"Key": f"{prefix}.md"},
                    {"Key": f"{prefix}.pdf"},
                ]
            },
        )

    def test_returns_zero_when_no_objects_found(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        # Paginator returns an empty page
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": []}]
        s3_client.get_paginator.return_value = mock_paginator

        count = repo.delete_outputs("2026-03-01")

        assert count == 0
        s3_client.delete_objects.assert_not_called()

    def test_returns_zero_when_page_has_no_contents_key(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        # S3 omits Contents key entirely when bucket prefix has no matches
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{}]
        s3_client.get_paginator.return_value = mock_paginator

        count = repo.delete_outputs("2026-03-01")

        assert count == 0
        s3_client.delete_objects.assert_not_called()

    def test_with_label_and_event_type(
        self, repo: S3OutputRepository, s3_client: MagicMock
    ):
        prefix = f"orgs/{ORG_ID}/setlists/youth/2026-03-01_evening"
        page = {"Contents": [{"Key": f"{prefix}.md"}]}
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [page]
        s3_client.get_paginator.return_value = mock_paginator

        count = repo.delete_outputs("2026-03-01", label="evening", event_type="youth")

        assert count == 1
        mock_paginator.paginate.assert_called_once_with(
            Bucket=BUCKET, Prefix=prefix
        )


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    def test_uses_provided_client(self, s3_client: MagicMock):
        repo = S3OutputRepository(
            bucket="b", org_id="o", s3_client=s3_client
        )
        assert repo._client is s3_client

    def test_creates_client_via_boto3_when_none(self):
        mock_client = MagicMock()
        with patch("library.repositories.s3.output.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            repo = S3OutputRepository(bucket="b", org_id="o")

        mock_boto3.client.assert_called_once_with("s3", endpoint_url=None)
        assert repo._client is mock_client

    def test_passes_endpoint_url_to_boto3(self):
        with patch("library.repositories.s3.output.boto3") as mock_boto3:
            S3OutputRepository(
                bucket="b", org_id="o", endpoint_url="http://minio:9000"
            )

        mock_boto3.client.assert_called_once_with(
            "s3", endpoint_url="http://minio:9000"
        )

    def test_raises_import_error_when_boto3_missing(self):
        with patch("library.repositories.s3.output.boto3", None):
            with pytest.raises(ImportError, match="boto3"):
                S3OutputRepository(bucket="b", org_id="o")
