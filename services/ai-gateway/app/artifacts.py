"""Short-lived D0 image artifact storage with strict format validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
from threading import RLock
from uuid import UUID, uuid4

from .provider import ImageArtifact
from .store import InvalidBoundaryError, NotFoundError


ALLOWED_MEDIA_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _dimensions(data: bytes, media_type: str) -> tuple[int, int]:
    if media_type == "image/png" and data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if media_type == "image/jpeg" and data[:2] == b"\xff\xd8":
        offset = 2
        while offset + 9 < len(data):
            if data[offset] != 0xFF:
                offset += 1
                continue
            marker = data[offset + 1]
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                return struct.unpack(">HH", data[offset + 5:offset + 9])[::-1]
            if offset + 4 > len(data):
                break
            size = struct.unpack(">H", data[offset + 2:offset + 4])[0]
            offset += max(2, size + 2)
    if media_type == "image/webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP" and len(data) >= 30:
        kind = data[12:16]
        if kind == b"VP8X":
            return (1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little"))
        if kind == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
            return (int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF)
    raise InvalidBoundaryError("artifact bytes do not match the declared media type")


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: UUID
    filename: str
    media_type: str
    sha256: str
    size_bytes: int
    width: int
    height: int
    created_at: datetime
    expires_at: datetime

    def payload(self) -> dict[str, object]:
        return {
            "artifactId": self.artifact_id, "filename": self.filename, "mediaType": self.media_type,
            "sha256": self.sha256, "sizeBytes": self.size_bytes, "width": self.width, "height": self.height,
            "classification": "D0", "createdAt": self.created_at, "expiresAt": self.expires_at,
        }


class ArtifactStore:
    def __init__(self, root: str, *, retention_hours: int, max_bytes: int) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass
        self.retention = timedelta(hours=retention_hours)
        self.max_bytes = max_bytes
        self._lock = RLock()

    def _paths(self, artifact_id: UUID) -> tuple[Path, Path]:
        base = self.root / str(artifact_id)
        return base.with_suffix(".bin"), base.with_suffix(".json")

    def put(self, filename: str, media_type: str, data: bytes) -> ArtifactRecord:
        if media_type not in ALLOWED_MEDIA_TYPES:
            raise InvalidBoundaryError("only PNG, JPEG, and WebP artifacts are supported")
        if not data or len(data) > self.max_bytes:
            raise InvalidBoundaryError("artifact size is outside the permitted boundary")
        safe_name = Path(filename).name[:128]
        if not safe_name or safe_name != filename:
            raise InvalidBoundaryError("artifact filename is invalid")
        width, height = _dimensions(data, media_type)
        if width < 1 or height < 1 or width > 12000 or height > 12000 or width * height > 40_000_000:
            raise InvalidBoundaryError("artifact dimensions exceed the permitted boundary")
        now, artifact_id = datetime.now(timezone.utc), uuid4()
        record = ArtifactRecord(artifact_id, safe_name, media_type, hashlib.sha256(data).hexdigest(), len(data), width, height, now, now + self.retention)
        binary, metadata = self._paths(artifact_id)
        with self._lock:
            binary.write_bytes(data)
            metadata.write_text(json.dumps(record.payload(), default=str, separators=(",", ":")), encoding="utf-8")
            try:
                os.chmod(binary, 0o600); os.chmod(metadata, 0o600)
            except OSError:
                pass
        return record

    def _load(self, artifact_id: UUID) -> ArtifactRecord:
        binary, metadata = self._paths(artifact_id)
        if not binary.exists() or not metadata.exists():
            raise NotFoundError("artifact not found")
        raw = json.loads(metadata.read_text(encoding="utf-8"))
        record = ArtifactRecord(
            UUID(raw["artifactId"]), raw["filename"], raw["mediaType"], raw["sha256"], int(raw["sizeBytes"]),
            int(raw["width"]), int(raw["height"]), datetime.fromisoformat(raw["createdAt"]), datetime.fromisoformat(raw["expiresAt"]),
        )
        if record.expires_at <= datetime.now(timezone.utc):
            self.delete(artifact_id)
            raise NotFoundError("artifact expired")
        return record

    def get(self, artifact_id: UUID) -> ArtifactRecord:
        with self._lock:
            return self._load(artifact_id)

    def image(self, artifact_id: UUID) -> ImageArtifact:
        with self._lock:
            record = self._load(artifact_id)
            binary, _ = self._paths(artifact_id)
            data = binary.read_bytes()
            if hashlib.sha256(data).hexdigest() != record.sha256:
                raise InvalidBoundaryError("artifact integrity validation failed")
            return ImageArtifact(str(artifact_id), record.media_type, data, record.sha256)

    def delete(self, artifact_id: UUID) -> bool:
        binary, metadata = self._paths(artifact_id)
        existed = binary.exists() or metadata.exists()
        with self._lock:
            binary.unlink(missing_ok=True); metadata.unlink(missing_ok=True)
        return existed

    def purge_expired(self) -> int:
        removed = 0
        for metadata in self.root.glob("*.json"):
            try:
                artifact_id = UUID(metadata.stem)
                self._load(artifact_id)
            except NotFoundError:
                removed += 1
            except (ValueError, OSError, json.JSONDecodeError):
                continue
        return removed
