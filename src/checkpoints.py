"""Local generation checkpoints and content-based export freshness checks."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

SPONTANEOUS_PROGRESS_PATH = Path(__file__).resolve().parents[1] / 'user_data' / 'spontaneous-progress.json'


def load_spontaneous_progress(topic, model):
    try:
        saved = load_checkpoint(SPONTANEOUS_PROGRESS_PATH)
    except FileNotFoundError:
        return None
    if (saved.get('topic'), saved.get('model')) != (topic, model):
        return None
    progress = saved.get('progress')
    if not isinstance(progress, dict):
        raise ValueError('Saved generation progress is invalid.')
    return progress


def save_spontaneous_progress(topic, model, progress):
    save_checkpoint(SPONTANEOUS_PROGRESS_PATH, {'topic': topic, 'model': model, 'progress': progress})


def clear_spontaneous_progress(topic, model, progress):
    if progress is not None and load_spontaneous_progress(topic, model) == progress:
        SPONTANEOUS_PROGRESS_PATH.unlink(missing_ok=True)


def content_fingerprint(content: dict) -> str:
    """Include all inputs (including event metadata) in the export identity."""
    if not isinstance(content, dict):
        raise ValueError('Checkpoint content must be a JSON object')
    encoded = json.dumps(content, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def save_checkpoint(path: Path, content: dict) -> str:
    """Atomically save JSON content; a failed write preserves the previous file."""
    fingerprint = content_fingerprint(content)
    payload = json.dumps({'checkpoint_version': 1, 'fingerprint': fingerprint,
                          'content': content}, ensure_ascii=False, indent=2,
                         allow_nan=False)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         dir=path.parent, delete=False,
                                         suffix='.tmp') as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return fingerprint


def load_checkpoint(path: Path) -> dict:
    """Reject damaged or unsupported checkpoints without modifying them."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if (not isinstance(data, dict)
            or set(data) != {'checkpoint_version', 'fingerprint', 'content'}
            or type(data['checkpoint_version']) is not int
            or data['checkpoint_version'] != 1
            or not isinstance(data['content'], dict)
            or data['fingerprint'] != content_fingerprint(data['content'])):
        raise ValueError('Invalid or unsupported generation checkpoint')
    return data['content']


def artifact_is_current(path: Path, source_fingerprint: str, content: dict) -> bool:
    """An existing export is usable only for the inputs it was built from."""
    return Path(path).is_file() and source_fingerprint == content_fingerprint(content)
