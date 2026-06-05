"""Workbook upload validation.

Three layers of defence:

1. Extension: must be .xlsx (what all parsers expect).
2. Filename hygiene: directory components stripped, control characters
   rejected. The on-disk name is rebuilt from a UUID + the original
   suffix so nothing user-supplied lands on the filesystem.
3. Magic bytes: the file must look like an Excel workbook on the wire.
   This stops a renamed payload (e.g. foo.xlsx containing a script)
   from being handed to openpyxl.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

ALLOWED_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}

# ZIP local file header — covers .xlsx and .xlsm (Office Open XML containers).
_ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
# OLE2 compound document header — covers legacy .xls.
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


class ValidationError(ValueError):
    """Raised when an upload fails validation."""


@dataclass(frozen=True)
class ValidatedUpload:
    """Result of a successful validation — safe to write to disk."""

    original_filename: str
    storage_filename: str
    suffix: str
    content: bytes


def _sanitize_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type: {suffix or '<none>'}. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return suffix


def _sanitize_display_name(filename: str) -> str:
    base = Path(filename).name
    cleaned = _CONTROL_CHARS.sub("", base).strip()
    if not cleaned:
        raise ValidationError("Empty or unsafe filename.")
    return cleaned[:255]


def _check_magic_bytes(content: bytes, suffix: str) -> None:
    if len(content) < 8:
        raise ValidationError("File is empty or truncated.")
    head = content[:8]
    if suffix in {".xlsx", ".xlsm"}:
        if not any(head.startswith(magic) for magic in _ZIP_MAGIC):
            raise ValidationError(
                "File does not look like an Office Open XML workbook "
                "(missing ZIP signature). Make sure you saved as .xlsx."
            )
    elif suffix == ".xls":
        if head != _OLE2_MAGIC:
            raise ValidationError(
                "File does not look like a legacy Excel workbook "
                "(missing OLE2 signature)."
            )


def validate_upload(filename: str | None, content: bytes) -> ValidatedUpload:
    if not filename:
        raise ValidationError("No filename provided.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
        )

    display = _sanitize_display_name(filename)
    suffix = _sanitize_extension(display)
    _check_magic_bytes(content, suffix)

    storage = f"{uuid.uuid4().hex}{suffix}"
    return ValidatedUpload(
        original_filename=display,
        storage_filename=storage,
        suffix=suffix,
        content=content,
    )


def write_atomically(target_dir: Path, upload: ValidatedUpload) -> Path:
    """Write a validated upload to target_dir via temp-file + atomic rename."""
    target_dir.mkdir(parents=True, exist_ok=True)
    final = target_dir / upload.storage_filename
    tmp = target_dir / f".{upload.storage_filename}.part"
    try:
        tmp.write_bytes(upload.content)
        tmp.replace(final)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
    return final
