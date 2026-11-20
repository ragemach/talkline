"""Explicit user defaults, stored locally beside the application, never invented by AI."""
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit


SETTINGS_PATH = Path(__file__).resolve().parents[1] / 'user_data' / 'settings.json'


@dataclass(frozen=True)
class EventDetails:
    venue: str = ''
    date: str = ''
    time: str = ''
    feedback_url: str = ''

    def __post_init__(self):
        for key in ('venue', 'date', 'time'):
            value = getattr(self, key)
            if not isinstance(value, str) or len(value) > 60:
                raise ValueError(f'{key}: use at most 60 characters.')
            object.__setattr__(self, key, value.strip())
        if not isinstance(self.feedback_url, str) or len(self.feedback_url) > 500:
            raise ValueError('Feedback URL must be text of at most 500 characters.')
        url = self.feedback_url.strip()
        if url:
            parts = urlsplit(url)
            if parts.scheme not in ('http', 'https') or not parts.netloc or any(c.isspace() for c in url):
                raise ValueError('Feedback URL must be a complete http:// or https:// address, or blank.')
        object.__setattr__(self, 'feedback_url', url)


@dataclass(frozen=True)
class UserSettings:
    event: EventDetails = EventDetails()
    model: str = 'qwen3:8b'

    def __post_init__(self):
        if not isinstance(self.event, EventDetails):
            raise ValueError('Invalid event settings.')
        if not isinstance(self.model, str) or not self.model.strip() or len(self.model) > 120:
            raise ValueError('Invalid local model name.')
        if 'cloud' in self.model.casefold() or any(c.isspace() for c in self.model):
            raise ValueError('Select a local downloaded model, not a cloud model.')


def load_settings(path: Path = SETTINGS_PATH) -> UserSettings:
    if not path.exists():
        return UserSettings()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or set(data) != {'version', 'event', 'model'} or data['version'] != 1:
            raise ValueError('Unknown settings format.')
        return UserSettings(event=EventDetails(**data['event']), model=data['model'])
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError(f'Cannot read saved settings: {exc}. The file has not been overwritten.') from exc


def save_settings(settings: UserSettings, path: Path = SETTINGS_PATH) -> None:
    """Atomic replacement avoids half-written settings after a crash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {'version': 1, **asdict(settings)}
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         suffix='.tmp', delete=False) as temp:
            temp_path = Path(temp.name)
            json.dump(data, temp, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
