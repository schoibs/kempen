from __future__ import annotations


CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "video/mp4": "mp4",
}


def upload_object_key(*, tenant_id: str, asset_id: str, content_type: str) -> str:
    return (
        f"tenants/{_segment(tenant_id)}/uploads/{_segment(asset_id)}/"
        f"product.{extension_for_content_type(content_type)}"
    )


def campaign_artifact_key(
    *,
    tenant_id: str,
    campaign_id: str,
    role: str,
    content_type: str,
) -> str:
    base_key = f"tenants/{_segment(tenant_id)}/campaigns/{_segment(campaign_id)}"
    extension = extension_for_content_type(content_type)
    filenames = {
        "product_input": f"input/product.{extension}",
        "storyboard": f"storyboard/storyboard.{extension}",
        "campaign_video": f"video/campaign.{extension}",
    }
    try:
        return f"{base_key}/{filenames[role]}"
    except KeyError as exc:
        raise ValueError(f"Unsupported asset role: {role}") from exc


def extension_for_content_type(content_type: str) -> str:
    try:
        return CONTENT_TYPE_EXTENSIONS[content_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported content type: {content_type}") from exc


def _segment(value: str) -> str:
    if not value or "/" in value or "\\" in value:
        raise ValueError("Object key segments must not be empty or contain path separators.")
    return value
