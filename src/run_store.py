"""Keep the most recent draft and its matching export in one local file."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from zipfile import BadZipFile, ZipFile
from zlib import error as CompressionError

from src.checkpoints import content_fingerprint


RUN_PATH = Path(__file__).resolve().parents[1] / 'user_data' / 'last_run.zip'
_MANIFEST_MEMBER = 'run.json'
_PACKAGE_MEMBER = 'kit.zip'
_MANIFEST_LIMIT = 8 * 1024 * 1024
_PACKAGE_LIMIT = 256 * 1024 * 1024
_PACKAGE_WARNING = 'The last export could not be opened. Your saved draft is available to export again.'


@dataclass(frozen=True)
class SavedRun:
    draft: dict
    package: bytes | None = None
    export_revision: str | None = None
    warning: str | None = None


def save_run(
    draft: dict,
    *,
    package: bytes | None = None,
    export_revision: str | None = None,
    path: Path | None = None,
) -> None:
    """Replace the previous run only after the complete new file is written."""
    if package is None:
        if export_revision is not None:
            raise ValueError('An export revision requires a package.')
        package_digest = None
    else:
        if not isinstance(package, bytes) or not 0 < len(package) <= _PACKAGE_LIMIT:
            raise ValueError('The export package is empty or exceeds the local save limit.')
        if not isinstance(export_revision, str) or not export_revision.strip():
            raise ValueError('A package requires an export revision.')
        package_digest = hashlib.sha256(package).hexdigest()

    manifest = {
        'version': 1,
        'draft': draft,
        'draft_sha256': content_fingerprint(draft),
        'package_sha256': package_digest,
        'export_revision': export_revision,
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(manifest_bytes) > _MANIFEST_LIMIT:
        raise ValueError('The draft exceeds the local save limit.')

    target = RUN_PATH if path is None else Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False, suffix='.tmp') as temporary:
            temporary_path = Path(temporary.name)
            with ZipFile(temporary, 'w') as archive:
                archive.writestr(_MANIFEST_MEMBER, manifest_bytes)
                if package is not None:
                    archive.writestr(_PACKAGE_MEMBER, package)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _read_member(archive: ZipFile, name: str, limit: int) -> bytes:
    entries = [entry for entry in archive.infolist() if entry.filename == name]
    if len(entries) != 1 or not 0 < entries[0].file_size <= limit:
        raise ValueError(f'Invalid saved run member: {name}')
    with archive.open(entries[0]) as stream:
        data = stream.read(limit + 1)
    if len(data) != entries[0].file_size:
        raise ValueError(f'Incomplete saved run member: {name}')
    return data


def _load_manifest(archive: ZipFile) -> dict:
    manifest = json.loads(_read_member(archive, _MANIFEST_MEMBER, _MANIFEST_LIMIT).decode('utf-8'))
    if (not isinstance(manifest, dict)
            or set(manifest) != {'version', 'draft', 'draft_sha256', 'package_sha256', 'export_revision'}
            or type(manifest['version']) is not int
            or manifest['version'] != 1
            or manifest['draft_sha256'] != content_fingerprint(manifest['draft'])):
        raise ValueError('Invalid document or unsupported saved run version.')

    digest = manifest['package_sha256']
    revision = manifest['export_revision']
    if digest is None:
        if revision is not None:
            raise ValueError('Invalid export metadata.')
    elif (not isinstance(digest, str) or re.fullmatch('[0-9a-f]{64}', digest) is None
          or not isinstance(revision, str) or not revision.strip()):
        raise ValueError('Invalid export metadata.')
    return manifest


def load_run(path: Path | None = None) -> SavedRun | None:
    """Load a saved draft. A damaged export can be rebuilt from the draft."""
    target = RUN_PATH if path is None else Path(path)
    try:
        archive = ZipFile(target)
    except FileNotFoundError:
        return None
    except BadZipFile as exc:
        raise ValueError('The saved run file is damaged.') from exc

    member_errors = (ValueError, BadZipFile, RuntimeError, EOFError, CompressionError)
    with archive:
        try:
            manifest = _load_manifest(archive)
        except member_errors as exc:
            raise ValueError('The saved draft is damaged or uses an unsupported format.') from exc
        draft = manifest['draft']
        digest = manifest['package_sha256']
        if digest is None:
            return SavedRun(draft)
        try:
            package = _read_member(archive, _PACKAGE_MEMBER, _PACKAGE_LIMIT)
            if hashlib.sha256(package).hexdigest() != digest:
                raise ValueError('The saved export checksum does not match.')
        except (*member_errors, OSError):
            return SavedRun(draft, warning=_PACKAGE_WARNING)
        return SavedRun(draft, package, manifest['export_revision'])
