from __future__ import annotations

import asyncio

import httpx
import structlog
from supabase import Client, create_client

from app.config import settings
from app.shared.exceptions import ExternalServiceException

logger = structlog.get_logger()

_PDF_MAGIC = b"%PDF"


def _validate_pdf_bytes(data: bytes) -> bool:
    return data[:4] == _PDF_MAGIC


class StorageClient:

    def __init__(self) -> None:
        self._client: Client | None = None
        self._bucket_name = "compliance-vault"

    def _get_client(self) -> Client:
        if not self._client:
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
        return self._client

    async def get_upload_url(self, storage_path: str, content_type: str) -> str:
        try:
            client = self._get_client()
            response = await asyncio.to_thread(
                lambda: client.storage.from_(self._bucket_name).create_signed_upload_url(
                    path=storage_path,
                    options={"contentType": "application/pdf"}
                )
            )
            if isinstance(response, dict) and response.get("error"):
                raise ExternalServiceException("Supabase Storage", response["error"]["message"])
            if isinstance(response, dict):
                url = response.get("signedURL") or response.get("signedUrl") or response.get("signed_url")
                if url:
                    return url
            if hasattr(response, "signed_url") and response.signed_url:
                return response.signed_url
            raise ExternalServiceException("Supabase Storage", f"Unexpected response shape: {response}")
        except ExternalServiceException:
            raise
        except Exception as e:
            raise ExternalServiceException("Supabase Storage", f"Failed to generate upload URL: {e}")

    async def get_download_url(self, storage_path: str, expires_in: int = 3600) -> str:
        try:
            client = self._get_client()
            response = await asyncio.to_thread(
                lambda: client.storage.from_(self._bucket_name).create_signed_url(
                    path=storage_path,
                    expires_in=expires_in
                )
            )
            # Supabase SDK returns different shapes depending on version
            if isinstance(response, dict):
                if response.get("error"):
                    raise ExternalServiceException("Supabase Storage", response["error"]["message"])
                url = response.get("signedURL") or response.get("signedUrl") or response.get("signed_url")
                if url:
                    return url
            # Newer SDK returns an object with attribute
            if hasattr(response, "signed_url") and response.signed_url:
                return response.signed_url
            if hasattr(response, "signedURL") and response.signedURL:
                return response.signedURL
            raise ExternalServiceException("Supabase Storage", f"Unexpected response shape: {response}")
        except ExternalServiceException:
            raise
        except Exception as e:
            raise ExternalServiceException("Supabase Storage", f"Failed to generate download URL: {e}")

    async def download_file(self, storage_path: str) -> bytes:
        try:
            download_url = await self.get_download_url(storage_path, expires_in=3600)
            async with httpx.AsyncClient() as client:
                response = await client.get(download_url)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as e:
            raise ExternalServiceException("Supabase Storage", f"Failed to download file: {e}")
        except ExternalServiceException:
            raise
        except Exception as e:
            raise ExternalServiceException("Supabase Storage", f"Failed to download file: {e}")

    async def upload_file(self, storage_path: str, file_data: bytes, content_type: str) -> str:
        if not _validate_pdf_bytes(file_data):
            raise ExternalServiceException("Storage", "Only valid PDF files are accepted")

        if len(file_data) > settings.MAX_FILE_SIZE:
            raise ExternalServiceException(
                "Storage", f"File exceeds maximum size of {settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )

        try:
            client = self._get_client()

            def _do_upload():
                bucket = client.storage.from_(self._bucket_name)
                return bucket.upload(
                    path=storage_path,
                    file=file_data,
                    file_options={
                        "content-type": "application/pdf",
                        "contentType": "application/pdf",
                    }
                )

            response = await asyncio.to_thread(_do_upload)

            if hasattr(response, "error") and response.error:
                raise ExternalServiceException("Supabase Storage", str(response.error))

            logger.info("file_uploaded", storage_path=storage_path, size=len(file_data))
            return await self.get_download_url(storage_path)

        except ExternalServiceException:
            raise
        except Exception as e:
            logger.error("file_upload_failed", storage_path=storage_path, error=str(e))
            raise ExternalServiceException("Supabase Storage", f"Failed to upload file: {e}")

    async def delete_file(self, storage_path: str) -> None:
        try:
            client = self._get_client()
            response = await asyncio.to_thread(
                lambda: client.storage.from_(self._bucket_name).remove([storage_path])
            )
            if isinstance(response, dict) and response.get("error"):
                raise ExternalServiceException("Supabase Storage", response["error"]["message"])
            logger.info("file_deleted", storage_path=storage_path)
        except ExternalServiceException:
            raise
        except Exception as e:
            raise ExternalServiceException("Supabase Storage", f"Failed to delete file: {e}")

    async def list_files(self, prefix: str) -> list[dict]:
        try:
            client = self._get_client()
            response = await asyncio.to_thread(
                lambda: client.storage.from_(self._bucket_name).list(path=prefix)
            )
            if isinstance(response, dict) and response.get("error"):
                raise ExternalServiceException("Supabase Storage", response["error"]["message"])
            return response if isinstance(response, list) else response.get("data", [])
        except ExternalServiceException:
            raise
        except Exception as e:
            raise ExternalServiceException("Supabase Storage", f"Failed to list files: {e}")
