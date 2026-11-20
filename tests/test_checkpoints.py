import json

import pytest

from src.checkpoints import (artifact_is_current, content_fingerprint,
                             load_checkpoint, save_checkpoint)


def test_roundtrip_preserves_multilingual_content_and_blank_metadata(tmp_path):
    content = {'event': {'date': ''}, 'meaning': 'sınır koymak'}
    path = tmp_path / 'session.json'
    identity = save_checkpoint(path, content)
    assert load_checkpoint(path) == content
    assert identity == content_fingerprint(dict(reversed(list(content.items()))))


@pytest.mark.parametrize('replacement', [
    {'event': {'date': '2026-12-01'}, 'topic': 'Boundaries'},
    {'event': {'date': ''}, 'topic': 'Travel'},
])
def test_changed_metadata_or_content_invalidates_export(tmp_path, replacement):
    content = {'event': {'date': ''}, 'topic': 'Boundaries'}
    artifact = tmp_path / 'deck.pptx'
    artifact.write_bytes(b'export')
    identity = content_fingerprint(content)
    assert artifact_is_current(artifact, identity, content)
    assert not artifact_is_current(artifact, identity, replacement)
    artifact.unlink()
    assert not artifact_is_current(artifact, identity, content)


def test_damaged_checkpoint_is_rejected_and_preserved(tmp_path):
    path = tmp_path / 'session.json'
    save_checkpoint(path, {'topic': 'Travel'})
    data = json.loads(path.read_text(encoding='utf-8'))
    data['content']['topic'] = 'Changed'
    path.write_text(json.dumps(data), encoding='utf-8')
    original = path.read_bytes()
    with pytest.raises(ValueError):
        load_checkpoint(path)
    assert path.read_bytes() == original


def test_failed_serialization_preserves_previous_checkpoint(tmp_path):
    path = tmp_path / 'session.json'
    save_checkpoint(path, {'topic': 'Travel'})
    with pytest.raises(ValueError):
        save_checkpoint(path, {'invalid': float('nan')})
    assert load_checkpoint(path) == {'topic': 'Travel'}
