import os
import cloudinary
import cloudinary.uploader

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_AVATAR_BYTES = 5 * 1024 * 1024


def _cloudinary_credentials():
    return (
        (os.getenv("CLOUDINARY_CLOUD_NAME") or "").strip(),
        (os.getenv("CLOUDINARY_API_KEY") or "").strip(),
        (os.getenv("CLOUDINARY_API_SECRET") or "").strip(),
    )


def is_cloudinary_configured():
    return all(_cloudinary_credentials())


def _safe_public_suffix(user_id):
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(user_id or "guest").strip())
    return cleaned or "guest"


def upload_user_avatar(file_obj, user_id):
    if file_obj is None:
        return None, "Please choose an image file to upload."
    filename = str(getattr(file_obj, "name", "") or "").strip()
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return None, "Only JPG, PNG, WEBP, or GIF images are allowed."
    file_size = getattr(file_obj, "size", None)
    if file_size is not None:
        if int(file_size) <= 0:
            return None, "Selected image file is empty."
        if int(file_size) > MAX_AVATAR_BYTES:
            return None, "Image size must be 5 MB or smaller."
    if not is_cloudinary_configured():
        return None, "Cloudinary credentials are not configured."
    cloud_name, api_key, api_secret = _cloudinary_credentials()
    try:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True)
        result = cloudinary.uploader.upload(
            file_obj,
            folder="edupredict/avatars",
            public_id=f"user_{_safe_public_suffix(user_id)}",
            overwrite=True,
            resource_type="image",
            transformation=[
                {
                    "width": 320,
                    "height": 320,
                    "crop": "fill",
                    "gravity": "face",
                    "quality": "auto",
                    "fetch_format": "auto",
                }
            ],
        )
        url = str((result or {}).get("secure_url") or (result or {}).get("url") or "").strip()
        if not url:
            return None, "Image upload failed: empty media URL returned."
        return url, None
    except Exception as exc:
        return None, f"Image upload failed: {exc}"
