import cloudinary.uploader
from fastapi import UploadFile, HTTPException

import cloudinary
from app.config import settings
import re
from urllib.parse import urlparse


def configure_cloudinary():
    """Initializes the Cloudinary configuration."""
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True  # Ensure URLs are HTTPS
    )


def upload_media_to_cloudinary(file: UploadFile, folder: str, public_id: str = None,
                               resource_type: str = 'image') -> str:
    """
    Uploads a file to Cloudinary and supports different resource types (image, video, raw).

    Args:
        file (UploadFile): The file from the FastAPI request.
        folder (str): Destination folder in Cloudinary.
        public_id (str, optional): Specific public_id to use.
        resource_type (str): 'image' (default), 'video', or 'raw'.

    Returns:
        str: The secure URL of the uploaded resource.

    Raises:
        HTTPException: If upload fails or Cloudinary doesn't return a URL.
    """
    try:
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder=folder,
            public_id=public_id,
            overwrite=True,
            resource_type=resource_type
        )

        secure_url = upload_result.get("secure_url")
        if not secure_url:
            raise HTTPException(status_code=500, detail="Cloudinary did not return a secure URL.")

        return secure_url
    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        raise HTTPException(status_code=500, detail=f"Could not upload media: {e}")


def upload_image_to_cloudinary(file: UploadFile, folder: str, public_id: str = None) -> str:
    """Compatibility wrapper for image uploads."""
    return upload_media_to_cloudinary(file=file, folder=folder, public_id=public_id, resource_type='image')


def delete_image_from_cloudinary(public_id: str, resource_type: str = 'image'):
    """
    Deletes a resource from Cloudinary using its public ID and optional resource type.

    Args:
        public_id (str): The full public_id of the resource (e.g., 'sambandha/profile_images/some_id').
        resource_type (str): 'image' (default) or 'video'.
    """
    try:
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)
    except Exception as e:
        # Log the error but don't raise an exception to the user,
        # as the primary action (deleting from DB) might have succeeded.
        print(f"Could not delete resource {public_id} from Cloudinary: {e}")


def get_public_id_from_url(url: str) -> str | None:
    """
    Extracts the Cloudinary public_id (including folder path) from a Cloudinary secure URL.

    Works by finding the "/upload/" segment in the path and removing any version prefix (v12345)
    and the file extension.

    Returns the public_id string (e.g. 'sambandha/profile_images/some_id') or None if parsing fails.
    """
    try:
        parsed = urlparse(url)
        path = parsed.path
        idx = path.find('/upload/')
        if idx == -1:
            return None
        public_path = path[idx + len('/upload/'):]
        # Strip leading version segment like v12345/
        public_path = re.sub(r'^v\d+/', '', public_path)
        # Remove potential query params (shouldn't be present after urlparse) and extension
        public_id = public_path.rsplit('.', 1)[0]
        # Remove leading slash if present
        if public_id.startswith('/'):
            public_id = public_id[1:]
        return public_id
    except Exception as e:
        print(f"Could not extract public_id from URL {url}: {e}")
        return None
