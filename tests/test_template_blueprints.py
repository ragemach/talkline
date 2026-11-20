from pathlib import Path

import pytest

from src.template_blueprints import inspect_spontaneous_template, verify_blueprint_source


SOURCE = Path(__file__).resolve().parents[1] / 'references/Completed_Spontaneous_Talk_23_Slides_READABLE.pptx'


def test_reference_inventory_includes_grouped_teaching_content_and_play_button():
    before = SOURCE.read_bytes()
    blueprint = inspect_spontaneous_template(SOURCE)
    assert len(blueprint['slides']) == 23
    assert sum(s['role'] == 'discussion' for s in blueprint['slides']) == 10
    a2 = blueprint['slides'][2]['fields']
    assert any(f['shape_path'] == [12, 14] and 'I think' in f['sample_text'] for f in a2)
    assert any('PLAY' in f['sample_text'] for f in blueprint['slides'][20]['fields'])
    assert all(slide['fields'] for slide in blueprint['slides'])
    bound = [f['content_key'] for s in blueprint['slides'] for f in s['fields'] if f['content_key']]
    assert len(bound) == 48
    assert 'deck.round1.9.c1' in bound
    assert 'deck.cooldown.2' in bound
    assert SOURCE.read_bytes() == before
    verify_blueprint_source(blueprint, SOURCE)


def test_changed_template_rejected(tmp_path):
    blueprint = inspect_spontaneous_template(SOURCE)
    changed = tmp_path / 'changed.pptx'
    changed.write_bytes(SOURCE.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='changed'):
        verify_blueprint_source(blueprint, changed)
