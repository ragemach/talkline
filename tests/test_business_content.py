import pytest

from src import ai_content
from src.business_content import (
    generate_business,
    regenerate_business_section,
    validate_business,
)
from src.spontaneous_content import generate_spontaneous, validate_spontaneous


TOPIC = 'Business Beyond the Office'
MODEL = 'qwen3:8b'


def test_business_demo_uses_both_supplied_examples_without_ollama(monkeypatch):
    def unexpected_request(*args, **kwargs):
        pytest.fail('The offline Business Demo called Ollama')

    monkeypatch.setattr(ai_content, '_ask_json', unexpected_request)
    content = generate_business(TOPIC)
    assert validate_business(content) is content
    assert len(content['warmup']) == 3
    assert len(content['round1']) == 10
    assert content['round1'][9]['title'] == 'The Future of Work'
    game = content['game']
    assert game['mechanic'] == 'smart_or_sneaky'
    assert len(game['elementary']) == len(game['advanced']) == 20
    assert game['elementary'][0]['scenario'] == 'A shop shows “Only 2 left!” next to a bag.'
    assert game['elementary'][0]['outcome_a'] != game['elementary'][0]['outcome_b']
    with pytest.raises(ValueError):
        validate_spontaneous(content)


def test_business_generation_resumes_without_repeating_batches(monkeypatch, round_model_batches):
    demo = generate_business(TOPIC)
    game = demo['game']
    responses = [
        *round_model_batches[0], *round_model_batches[1],
        *[{'cards': game[level][start:start + 5]}
          for level in ('elementary', 'advanced') for start in (0, 5, 10, 15)],
        {key: demo[key] for key in ('subtitle', 'tagline', 'opening', 'closing')},
    ]
    snapshots = []

    def request(prompt, schema, model, *, think):
        assert TOPIC in prompt
        assert model == MODEL
        if 'choice_a' in str(schema):
            assert 'Smart or Sneaky?' in prompt
            assert 'two different plausible twists' in prompt
        return responses.pop(0)

    def fail_after_three(*args, **kwargs):
        if len(snapshots) >= 3:
            raise RuntimeError('Ollama stopped.')
        return request(*args, **kwargs)

    def report(completed, total, snapshot):
        assert total == 11
        snapshots.append((completed, snapshot))

    monkeypatch.setattr(ai_content, '_ask_json', fail_after_three)
    with pytest.raises(RuntimeError, match='Smart or Sneaky'):
        generate_business(TOPIC, MODEL, on_progress=report)
    assert [completed for completed, _ in snapshots] == [1, 2, 3]
    checkpoint = snapshots[-1][1]
    assert checkpoint['mechanic'] == 'smart_or_sneaky'
    assert len(checkpoint['game']['elementary']) == 5
    with pytest.raises(ValueError, match='mechanic'):
        generate_spontaneous(TOPIC, MODEL, resume=checkpoint)

    monkeypatch.setattr(ai_content, '_ask_json', request)
    generated = generate_business(TOPIC, MODEL, resume=checkpoint, on_progress=report)
    assert generated['round1'] == checkpoint['round1']
    assert generated['game'] == game
    assert not responses
    assert snapshots[-1][0] == 11
    assert generate_business(TOPIC, MODEL, resume=snapshots[-1][1]) == generated


def test_business_section_regeneration_keeps_other_content(monkeypatch):
    demo = generate_business(TOPIC)
    closing = 'Tell us one workplace decision you would make differently next time.'

    def request(prompt, schema, model, *, think):
        assert 'workplace decision' in prompt
        assert tuple(schema['properties']) == ('closing',)
        return {'closing': closing}

    monkeypatch.setattr(ai_content, '_ask_json', request)
    revised = regenerate_business_section(TOPIC, demo, 'closing', MODEL, 'Use a workplace decision')
    assert revised == {**demo, 'closing': closing}
