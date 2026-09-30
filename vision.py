"""Parse OpenAI chat image parts for upload through the Muse web composer."""

import base64
import binascii
from dataclasses import dataclass


MAX_IMAGE_BYTES = 10_000_000
MAX_IMAGES = 4
MAX_REQUEST_BYTES = 56_000_000

IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


class InvalidImageInput(ValueError):
    pass


@dataclass(frozen=True)
class ImageAttachment:
    name: str
    mime_type: str
    data: bytes

    def as_file_payload(self):
        return {"name": self.name, "mimeType": self.mime_type, "buffer": self.data}


def _detected_mime(data):
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _parse_image_url(part, number):
    image_url = part.get("image_url")
    url = image_url.get("url") if isinstance(image_url, dict) else image_url
    if not isinstance(url, str) or not url.startswith("data:"):
        raise InvalidImageInput(
            "Images must use a base64 data URL (data:image/...;base64,...); remote URLs are not supported"
        )

    header, separator, encoded = url.partition(",")
    if not separator or not header.lower().endswith(";base64"):
        raise InvalidImageInput("Image data URL must contain base64-encoded bytes")

    mime_type = header[5:-7].lower()
    if mime_type == "image/jpg":
        mime_type = "image/jpeg"
    if mime_type not in IMAGE_EXTENSIONS:
        raise InvalidImageInput("Supported image types: JPEG, PNG, GIF, and WebP")
    if len(encoded) > ((MAX_IMAGE_BYTES + 2) // 3) * 4 + 4:
        raise InvalidImageInput(f"Each image must be at most {MAX_IMAGE_BYTES} bytes")

    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise InvalidImageInput("Invalid base64 image data") from exc
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise InvalidImageInput(f"Each image must be at most {MAX_IMAGE_BYTES} bytes")
    if _detected_mime(data) != mime_type:
        raise InvalidImageInput("Image bytes do not match the declared MIME type")

    return ImageAttachment(f"image-{number}.{IMAGE_EXTENSIONS[mime_type]}", mime_type, data)


def parse_chat_messages(messages):
    """Return a text prompt and in-memory files from Chat Completions messages."""
    if not isinstance(messages, list):
        raise InvalidImageInput("messages must be an array")

    prompt_parts = []
    images = []
    has_text = False
    for message in messages:
        if not isinstance(message, dict):
            raise InvalidImageInput("Each message must be an object")
        role = message.get("role", "user")
        content = message.get("content", "")
        if isinstance(content, list):
            items = []
            for part in content:
                if not isinstance(part, dict):
                    raise InvalidImageInput("Each content part must be an object")
                if part.get("type") == "image_url":
                    if role != "user":
                        raise InvalidImageInput("Images are only supported in user messages")
                    if len(images) >= MAX_IMAGES:
                        raise InvalidImageInput(f"At most {MAX_IMAGES} images are supported per request")
                    image = _parse_image_url(part, len(images) + 1)
                    images.append(image)
                    items.append(f"[Image {len(images)} attached]")
                elif "text" in part:
                    text = part["text"]
                    if not isinstance(text, str):
                        raise InvalidImageInput("Text content must be a string")
                    if text.strip():
                        has_text = True
                    items.append(text)
                else:
                    raise InvalidImageInput(f"Unsupported content part type: {part.get('type')}")
            content = "\n".join(items)
        elif not isinstance(content, str):
            raise InvalidImageInput("Message content must be a string or an array")
        elif content.strip():
            has_text = True

        if role == "system":
            prompt_parts.append(f"[System Instruction]\n{content}")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}")
        else:
            prompt_parts.append(content)

    prompt = "\n\n".join(prompt_parts)
    if images and not has_text:
        prompt += "\nDescribe the attached image(s)."
    return prompt, images
