from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from src import run_store


def _kit(topic):
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as archive:
        archive.writestr('content.json', json.dumps({'topic': topic}))
    return buffer.getvalue()


def test_saved_draft_and_matching_export_roundtrip(tmp_path):
    path = tmp_path / 'user_data' / 'last_run.zip'
    draft = {'topic': 'Office Boundaries', 'note': 'sınır koymak', 'date': ''}
    package = _kit(draft['topic'])

    assert run_store.load_run(path) is None
    run_store.save_run(draft, path=path)
    assert run_store.load_run(path) == run_store.SavedRun(draft)

    run_store.save_run(draft, package=package, export_revision='revision', path=path)
    assert run_store.load_run(path) == run_store.SavedRun(draft, package, 'revision')


def test_failed_replacement_preserves_last_saved_run(tmp_path, monkeypatch):
    path = tmp_path / 'last_run.zip'
    draft = {'topic': 'Travel'}
    package = _kit(draft['topic'])
    run_store.save_run(draft, package=package, export_revision='old', path=path)
    old_bytes = path.read_bytes()

    def fail_replace(source, target):
        assert Path(source).parent == path.parent
        assert target == path
        raise PermissionError('simulated Windows file lock')

    monkeypatch.setattr(run_store.os, 'replace', fail_replace)
    with pytest.raises(PermissionError):
        run_store.save_run({'topic': 'Work'}, path=path)
    assert path.read_bytes() == old_bytes
    assert run_store.load_run(path) == run_store.SavedRun(draft, package, 'old')
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('damage', ['missing kit', 'damaged kit CRC', 'different kit'])
def test_export_damage_recovers_draft(tmp_path, damage):
    path = tmp_path / 'last_run.zip'
    draft = {'topic': 'Travel'}
    package = _kit(draft['topic'])
    run_store.save_run(draft, package=package, export_revision='old', path=path)
    if damage == 'damaged kit CRC':
        path.write_bytes(path.read_bytes().replace(package, b'X' * len(package), 1))
    else:
        with ZipFile(path) as archive:
            manifest = archive.read('run.json')
        with ZipFile(path, 'w') as archive:
            archive.writestr('run.json', manifest)
            if damage == 'different kit':
                archive.writestr('kit.zip', _kit('Work'))

    restored = run_store.load_run(path)
    assert restored.draft == draft
    assert restored.package is None and restored.export_revision is None
    assert restored.warning


@pytest.mark.parametrize('damage', ['truncated archive', 'changed draft'])
def test_invalid_draft_raises_without_overwriting_file(tmp_path, damage):
    path = tmp_path / 'last_run.zip'
    run_store.save_run({'topic': 'Travel'}, path=path)
    if damage == 'truncated archive':
        path.write_bytes(path.read_bytes()[:20])
    else:
        with ZipFile(path) as archive:
            manifest = json.loads(archive.read('run.json'))
        manifest['draft']['topic'] = 'Work'
        with ZipFile(path, 'w') as archive:
            archive.writestr('run.json', json.dumps(manifest))
    damaged_file = path.read_bytes()

    with pytest.raises(ValueError, match='damaged'):
        run_store.load_run(path)
    assert path.read_bytes() == damaged_file
