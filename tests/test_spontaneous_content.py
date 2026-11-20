from copy import deepcopy

import pytest

from src import ai_content
from src.spontaneous_content import (
    generate_spontaneous,
    regenerate_spontaneous_section,
    validate_spontaneous,
)


def test_demo_uses_complete_examples_without_ollama(monkeypatch):
    def avoid_ollama(*args, **kwargs):
        pytest.fail('Demo attempted to call Ollama')

    monkeypatch.setattr(ai_content, '_ask_json', avoid_ollama)
    demo = generate_spontaneous('Coffee shops')
    assert len(demo['round1']) == 10
    assert len(demo['warmup']) == 3
    assert len(demo['game']['elementary']) == len(demo['game']['advanced']) == 20
    assert all({*card} == {'title', 'a2', 'b2', 'c1'} for card in demo['round1'])
    demo['round1'][0]['title'] = 'Changed'
    assert generate_spontaneous('Coffee shops')['round1'][0]['title'] != 'Changed'


def test_local_batches_retry_a_duplicate_before_accepting_new_cards(monkeypatch):
    demo = generate_spontaneous('Coffee shops')
    cards = demo['round1']
    game = demo['game']
    answers = [
        {'cards': cards[:5]},
        {'cards': cards[:5]},  # Invalid second batch repeats already accepted cards.
        {'cards': cards[5:]},
        *[
            {'cards': game[level][start:start + 5]}
            for level in ('elementary', 'advanced') for start in range(0, 20, 5)
        ],
        {section: value for section, value in demo.items() if section not in ('round1', 'game')},
    ]
    prompts = []

    def ask(prompt, schema, model, *, think):
        prompts.append(prompt)
        assert model == 'qwen3:8b'
        assert 'Coffee shops' in prompt
        if 'cards' in schema['properties']:
            assert schema['properties']['cards']['maxItems'] == 5
        return answers.pop(0)

    monkeypatch.setattr(ai_content, '_ask_json', ask)
    actual = generate_spontaneous('Coffee shops', 'qwen3:8b')
    assert actual == demo
    assert not answers
    assert len(prompts) == 12
    assert 'Previous attempt failed' in prompts[2]
    assert 'duplicate' in prompts[2]


def test_single_section_edit_preserves_other_content(monkeypatch):
    demo = generate_spontaneous('Coffee shops')
    baseline = deepcopy(demo)
    closing = 'Share a decision from the discussion and explain whether your game changed it.'

    def ask(prompt, schema, model, *, think):
        assert list(schema['properties']) == ['closing']
        assert 'Mention the choices' in prompt
        return {'closing': closing}

    monkeypatch.setattr(ai_content, '_ask_json', ask)
    revised = regenerate_spontaneous_section(
        'Coffee shops', demo, 'closing', 'qwen3:8b', 'Mention the choices',
    )
    assert revised == {**baseline, 'closing': closing}
    assert demo == baseline


def test_failed_section_retries_are_bounded_and_original_stays_available(monkeypatch):
    demo = generate_spontaneous('Coffee shops')
    baseline = deepcopy(demo)
    calls = []

    def ask(*args, **kwargs):
        calls.append(1)
        return {'cards': []}

    monkeypatch.setattr(ai_content, '_ask_json', ask)
    with pytest.raises(ValueError, match='Round 1, cards 1 to 5'):
        regenerate_spontaneous_section('Coffee shops', demo, 'round1', 'qwen3:8b')
    assert len(calls) == 2
    assert demo == baseline


@pytest.mark.parametrize('invalid_topic', [None, '   ', 'x' * 111])
def test_invalid_topic_is_rejected_before_generation(invalid_topic):
    with pytest.raises(ValueError, match='Topic'):
        generate_spontaneous(invalid_topic)


def test_full_validation_rejects_same_question_at_multiple_levels():
    draft = generate_spontaneous('Coffee shops')
    draft['round1'][0]['b2'] = draft['round1'][0]['a2']
    with pytest.raises(ValueError, match='Round 1 questions.*duplicate'):
        validate_spontaneous(draft)


def test_resume_retains_valid_batches_after_a_connection_failure(monkeypatch):
    topic = 'Coffee shops'
    model = 'qwen3:8b'
    demo = generate_spontaneous(topic)
    rounds = demo['round1']
    game = demo['game']
    first_answers = [{'cards': rounds[:5]}, {'cards': rounds[5:]},
                     {'cards': game['elementary'][:5]}]
    snapshots = []

    def ask_first(*args, **kwargs):
        if first_answers:
            return first_answers.pop(0)
        raise RuntimeError('connection was lost')

    def report(completed, total, checkpoint):
        assert total == 11
        snapshots.append((completed, checkpoint))

    monkeypatch.setattr(ai_content, '_ask_json', ask_first)
    with pytest.raises(RuntimeError, match='Patch Notes elementary, cards 6 to 10'):
        generate_spontaneous(topic, model, on_progress=report)
    assert [completed for completed, _ in snapshots] == [1, 2, 3]
    assert len(snapshots[0][1]['round1']) == 5
    checkpoint = snapshots[-1][1]
    assert len(checkpoint['game']['elementary']) == 5
    remaining_answers = [
        *[{'cards': game['elementary'][start:start + 5]} for start in range(5, 20, 5)],
        *[{'cards': game['advanced'][start:start + 5]} for start in range(0, 20, 5)],
        {section: value for section, value in demo.items() if section not in ('round1', 'game')},
    ]
    monkeypatch.setattr(ai_content, '_ask_json', lambda *args, **kwargs: remaining_answers.pop(0))
    resumed = generate_spontaneous(topic, model, resume=checkpoint, on_progress=report)
    assert not remaining_answers
    assert resumed == demo
    assert len(checkpoint['game']['elementary']) == 5
    assert snapshots[-1][0] == 11
    assert generate_spontaneous(topic, model, resume=snapshots[-1][1]) == demo
    with pytest.raises(ValueError, match='topic:'):
        generate_spontaneous('Beach holidays', model, resume=checkpoint)
