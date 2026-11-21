import base64
import os
import uuid
from urllib.parse import urlparse
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


def _configure_cloudinary():
    cloud_name, api_key, api_secret = _cloudinary_credentials()
    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True)


def _validate_image_file(file_obj):
    if file_obj is None:
        return "Please choose an image file to upload."
    filename = str(getattr(file_obj, "name", "") or "").strip()
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return "Only JPG, PNG, WEBP, or GIF images are allowed."
    file_size = getattr(file_obj, "size", None)
    if file_size is not None:
        if int(file_size) <= 0:
            return "Selected image file is empty."
        if int(file_size) > MAX_AVATAR_BYTES:
            return "Image size must be 5 MB or smaller."
    return None


def extract_cloudinary_public_id(url):
    raw = str(url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or "cloudinary" not in (parsed.netloc or "").lower():
        return ""
    if "/upload/" not in parsed.path:
        return ""
    after_upload = parsed.path.split("/upload/", 1)[1]
    segments = [seg for seg in after_upload.split("/") if seg]
    if not segments:
        return ""
    version_idx = next((i for i, seg in enumerate(segments) if seg.startswith("v") and len(seg) > 1 and seg[1:].isdigit()), None)
    if version_idx is not None:
        segments = segments[version_idx + 1:]
    else:
        while segments and ("," in segments[0] or segments[0].startswith("t_")):
            segments.pop(0)
    if not segments:
        return ""
    if "." in segments[-1]:
        segments[-1] = segments[-1].rsplit(".", 1)[0]
    return "/".join(seg for seg in segments if seg)


def destroy_cloudinary_asset(url="", default_public_id=""):
    public_id = extract_cloudinary_public_id(url) or str(default_public_id or "").strip()
    if not public_id or not is_cloudinary_configured():
        return False
    try:
        _configure_cloudinary()
        result = cloudinary.uploader.destroy(public_id, invalidate=True)
        if isinstance(result, dict) and "result" in result:
            return str(result.get("result") or "").strip().lower() in ("ok", "not found")
        return True
    except Exception:
        return False


def _upload_to_cloudinary(file_obj, folder, public_id, transformation, overwrite=True):
    if err := _validate_image_file(file_obj):
        return None, err
    if not is_cloudinary_configured():
        return None, "Cloudinary credentials are not configured."
    try:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        _configure_cloudinary()
        result = cloudinary.uploader.upload(
            file_obj,
            folder=folder,
            public_id=public_id,
            overwrite=overwrite,
            resource_type="image",
            transformation=transformation,
        )
        url = str((result or {}).get("secure_url") or (result or {}).get("url") or "").strip()
        if not url:
            return None, "Image upload failed: empty media URL returned."
        return url, None
    except Exception as exc:
        return None, f"Image upload failed: {exc}"


def upload_user_avatar(file_obj, user_id):
    public_id = f"user_{_safe_public_suffix(user_id)}_{uuid.uuid4().hex[:6]}"
    transform = [
        {
            "width": 320,
            "height": 320,
            "crop": "fill",
            "gravity": "face",
            "quality": "auto",
            "fetch_format": "auto",
        }
    ]
    return _upload_to_cloudinary(file_obj, "edupredict/avatars", public_id, transform, overwrite=True)


def upload_ticket_attachment(file_obj, user_id, index=0):
    public_id = f"ticket_{_safe_public_suffix(user_id)}_{int(index)}_{uuid.uuid4().hex[:8]}"
    transform = [{"quality": "auto", "fetch_format": "auto"}]
    return _upload_to_cloudinary(file_obj, "edupredict/tickets", public_id, transform, overwrite=False)


def encode_image_data_uri(file_obj, max_bytes=1048576):
    if _validate_image_file(file_obj):
        return ""
    ext = os.path.splitext(str(getattr(file_obj, "name", "") or "").strip())[1].lower()
    try:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        raw = file_obj.read()
    except Exception:
        return ""
    if not raw or len(raw) > max_bytes:
        return ""
    mime = "jpeg" if ext in (".jpg", ".jpeg") else ext.lstrip(".")
    return f"data:image/{mime};base64,{base64.b64encode(raw).decode('ascii')}"
