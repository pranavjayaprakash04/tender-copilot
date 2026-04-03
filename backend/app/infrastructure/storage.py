from __future__ import annotations

import httpx
import structlog
from supabase import Client, create_client

from app.config import settings
from app.shared.exceptions import ExternalServiceException

logger = structlog.get_logger()


class StorageClient:
    """Client for Supabase Storage operations."""

    def __init__(self) -> None:
        self._client: Client | None = None
        self._bucket_name = "vault-documents"

    def _get_client(self) -> Client:
        """Get Supabase client."""
        if not self._client:
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
        return self._client

    async def get_upload_url(self, storage_path: str, content_type: str) -> str:
        """Generate a signed upload URL for a file."""
        try:
            client = self._get_client()

            # Create signed URL for upload
            response = client.storage.from_(self._bucket_name).create_signed_upload_url(
                path=storage_path,
                options={
                    'contentType': content_type,
                    'upsert': True
                }
            )

            if response.get('error'):
                raise ExternalServiceException("Supabase Storage", response['error']['message'])

            signed_url = response['signedUrl']

            logger.info(
                "upload_url_generated",
                storage_path=storage_path,
                content_type=content_type
            )

            return signed_url

        except Exception as e:
            logger.error(
                "upload_url_generation_failed",
                storage_path=storage_path,
                error=str(e)
            )
            raise ExternalServiceException("Supabase Storage", f"Failed to generate upload URL: {e}")

    async def get_download_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Generate a signed download URL for a file."""
        try:
            client = self._get_client()

            # Create signed URL for download
            response = client.storage.from_(self._bucket_name).create_signed_url(
                path=storage_path,
                expires_in=expires_in
            )

            if response.get('error'):
                raise ExternalServiceException("Supabase Storage", response['error']['message'])

            signed_url = response['signedUrl']

            logger.info(
                "download_url_generated",
                storage_path=storage_path,
                expires_in=expires_in
            )

            return signed_url

        except Exception as e:
            logger.error(
                "download_url_generation_failed",
                storage_path=storage_path,
                error=str(e)
            )
            raise ExternalServiceException("Supabase Storage", f"Failed to generate download URL: {e}")

    async def download_file(self, storage_path: str) -> bytes:
        """Download file bytes from storage."""
        try:
            # Get download URL
            download_url = await self.get_download_url(storage_path, expires_in=3600)

            # Download file using httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(download_url)
                response.raise_for_status()

                file_bytes = response.content

                logger.info(
                    "file_downloaded",
                    storage_path=storage_path,
                    size=len(file_bytes)
                )

                return file_bytes

        except httpx.HTTPError as e:
            logger.error(
                "file_download_http_error",
                storage_path=storage_path,
                status_code=e.response.status_code if e.response else None,
                error=str(e)
            )
            raise ExternalServiceException("Supabase Storage", f"Failed to download file: {e}")
        except Exception as e:
            logger.error(
                "file_download_failed",
                storage_path=storage_path,
                error=str(e)
            )
            raise ExternalServiceException("Supabase Storage", f"Failed to download file: {e}")

    async def upload_file(self, storage_path: str, file_data: bytes, content_type: str) -> str:
        """Upload a file directly to storage."""
        try:
            client = self._get_client()

            # Upload file
            response = client.storage.from_(self._bucket_name).upload(
                path=storage_path,
                file=file_data,
                file_options={
                    'contentType': content_type,
                    'upsert': True
                }
            )

            if response.get('error'):
                raise ExternalServiceException("Supabase Storage", response['error']['message'])

            logger.info(
                "file_uploaded",
                storage_path=storage_path,
                size=len(file_data),
                content_type=content_type
            )

            # Return download URL
            return await self.get_download_url(storage_path)

        except Exception as e:
            logger.error(
                "file_upload_failed",
                storage_path=storage_path,
                error=str(e)
            )
            raise ExternalServiceException("Supabase Storage", f"Failed to upload file: {e}")

    async def delete_file(self, storage_path: str) -> None:
        """Delete a file from storage."""
        try:
            client = self._get_client()

            # Delete file
            response = client.storage.from_(self._bucket_name).remove([storage_path])

            if response.get('error'):
                raise ExternalServiceException("Supabase Storage", response['error']['message'])

            logger.info(
                "file_deleted",
                storage_path=storage_path
            )

        except Exception as e:
            logger.error(
                "file_deletion_failed",
                storage_path=storage_path,
                error=str(e)
            )
            raise ExternalServiceException("Supabase Storage", f"Failed to delete file: {e}")

    async def list_files(self, prefix: str) -> list[dict]:
        """List files with a given prefix."""
        try:
            client = self._get_client()

            # List files
            response = client.storage.from_(self._bucket_name).list(path=prefix)

            if response.get('error'):
                raise ExternalServiceException("Supabase Storage", response['error']['message'])

            files = response.get('data', [])

            logger.info(
                "files_listed",
                prefix=prefix,
                count=len(files)
            )

            return files

        except Exception as e:
            logger.error(
                "file_listing_failed",
                prefix=prefix,
                error=str(e)
            )
            raise ExternalServiceException("Supabase Storage", f"Failed to list files: {e}")

    async def get_file_info(self, storage_path: str) -> dict:
        """Get file metadata."""
        try:
            client = self._get_client()

            # Get file info
            response = client.storage.from_(self._bucket_name).get_metadata(storage_path)

            if response.get('error'):
                raise ExternalServiceException("Supabase Storage", response['error']['message'])

            metadata = response.get('data', {})

            logger.info(
                "file_info_retrieved",
                storage_path=storage_path
            )

            return metadata

        except Exception as e:
            logger.error(
                "file_info_retrieval_failed",
                storage_path=storage_path,
                error=str(e)
            )
            raise ExternalServiceException("Supabase Storage", f"Failed to get file info: {e}")
