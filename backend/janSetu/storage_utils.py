import os
import io
import re
import uuid
import base64
import requests
from PIL import Image
from django.conf import settings

def get_supabase_storage_config():
    """Retrieve Supabase Storage configuration from environment or settings."""
    supabase_url = os.environ.get('SUPABASE_URL') or getattr(settings, 'SUPABASE_URL', '')
    service_key = (
        os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or 
        os.environ.get('SUPABASE_KEY') or 
        getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', '')
    )
    bucket_name = os.environ.get('SUPABASE_STORAGE_BUCKET') or 'janseva-media'
    
    # Auto-extract supabase_url if SUPABASE_DB_URL is present and SUPABASE_URL is missing
    if not supabase_url:
        db_url = os.environ.get('SUPABASE_DB_URL') or getattr(settings, 'SUPABASE_DB_URL', '')
        if db_url and '@' in db_url and '.supabase.' in db_url:
            # Example: aws-0-ap-south-1.pooler.supabase.com -> extract ref if available
            pass

    return supabase_url.rstrip('/') if supabase_url else '', service_key, bucket_name


def upload_bytes_to_supabase_storage(image_bytes: bytes, file_path: str, content_type: str = 'image/jpeg') -> str:
    """Upload raw image bytes to Supabase Storage and return public URL.
    Returns empty string if not configured or on upload failure.
    """
    supabase_url, service_key, bucket_name = get_supabase_storage_config()
    if not supabase_url or not service_key:
        return ''

    upload_endpoint = f"{supabase_url}/storage/v1/object/{bucket_name}/{file_path}"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    try:
        resp = requests.post(upload_endpoint, data=image_bytes, headers=headers, timeout=8)
        if resp.status_code in [200, 201]:
            public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{file_path}"
            return public_url
        else:
            print(f"[Storage] Supabase upload failed ({resp.status_code}): {resp.text}")
            return ''
    except Exception as e:
        print(f"[Storage] Exception during Supabase upload: {e}")
        return ''


def compress_image_bytes(image_bytes: bytes, max_dim: int = 800, quality: int = 70) -> bytes:
    """Compress image bytes using PIL."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Convert RGBA/P to RGB for clean JPEG compression
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize if dimensions exceed max_dim
        width, height = img.size
        if width > max_dim or height > max_dim:
            if width > height:
                new_height = int((height * max_dim) / width)
                new_width = max_dim
            else:
                new_width = int((width * max_dim) / height)
                new_height = max_dim
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        out_io = io.BytesIO()
        img.save(out_io, format='JPEG', quality=quality, optimize=True)
        return out_io.getvalue()
    except Exception as e:
        print(f"[Storage] Image compression failed: {e}")
        return image_bytes


def process_media_string(media_str: str, folder: str = "media", prefix: str = "img", max_dim: int = 800, quality: int = 70) -> str:
    """Process a media string.
    - If already http/https URL: returns as-is.
    - If base64 data URI:
      1. Tries to upload compressed image to Supabase Storage (returns CDN URL).
      2. If Supabase Storage is not configured, returns compressed base64 (<35KB).
    """
    if not media_str or not isinstance(media_str, str):
        return media_str or ''

    media_str = media_str.strip()

    # Already a hosted URL
    if media_str.startswith('http://') or media_str.startswith('https://'):
        return media_str

    # Check if base64 data URI or raw base64
    if not (media_str.startswith('data:image/') or len(media_str) > 100):
        return media_str

    try:
        # Extract base64 payload
        if ';base64,' in media_str:
            header, base64_data = media_str.split(';base64,', 1)
        else:
            base64_data = media_str

        raw_bytes = base64.b64decode(base64_data)
        compressed_bytes = compress_image_bytes(raw_bytes, max_dim=max_dim, quality=quality)

        # 1. Try Supabase Storage upload
        file_name = f"{prefix}_{uuid.uuid4().hex[:10]}.jpg"
        file_path = f"{folder}/{file_name}"
        public_url = upload_bytes_to_supabase_storage(compressed_bytes, file_path, content_type='image/jpeg')

        if public_url:
            return public_url

        # 2. Fallback: Compact Data URI
        compact_b64 = base64.b64encode(compressed_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{compact_b64}"

    except Exception as e:
        print(f"[Storage] Failed to process media string: {e}")
        return media_str


def sanitize_avatar(avatar_str: str, user_identifier: str = "citizen") -> str:
    """Sanitize and compress user avatar. Avatars are small 200x200 thumbnails."""
    if not avatar_str:
        return f"https://api.dicebear.com/7.x/bottts/svg?seed={user_identifier}"
    
    return process_media_string(
        avatar_str,
        folder="avatars",
        prefix=f"avatar_{user_identifier}",
        max_dim=200,
        quality=70
    )


def sanitize_issue_images(images_data: dict, issue_id: str = "issue") -> dict:
    """Sanitize reported and resolved images in CivicIssue.images dict."""
    if not isinstance(images_data, dict):
        return images_data

    sanitized = {}
    for key, val in images_data.items():
        if isinstance(val, str) and val:
            sanitized[key] = process_media_string(
                val,
                folder="issues",
                prefix=f"{issue_id}_{key}",
                max_dim=800,
                quality=65
            )
        else:
            sanitized[key] = val
    return sanitized
