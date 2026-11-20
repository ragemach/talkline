from copy import deepcopy
import json

import pytest

from src import ai_content
from src.game_night_content import generate_game_night, validate_game_night


def test_demo_is_complete_and_works_without_ollama(monkeypatch):
    def no_ollama(*args, **kwargs):
        pytest.fail('Demo tried to call Ollama.')

    monkeypatch.setattr(ai_content, '_ask_json', no_ollama)
    content = generate_game_night('A Night Out')
    assert validate_game_night(content) is content
    assert set(content) == {'subtitle', 'tagline', 'opening', 'closing', 'warmup', 'games'}
    assert [game['mechanic'] for game in content['games']] == ['taboo', 'problem_solver']
    for game in content['games']:
        for level in ('elementary', 'advanced'):
            assert len(game[level]) == 20
    content['games'][0]['elementary'].clear()
    assert len(generate_game_night('A Night Out')['games'][0]['elementary']) == 20


def test_rejects_missing_swapped_or_duplicate_games_and_long_warmups():
    content = generate_game_night('A Night Out')
    for games in (content['games'][:1], content['games'][::-1], [content['games'][0]] * 2):
        with pytest.raises(ValueError):
            validate_game_night({**content, 'games': games})
    with pytest.raises(ValueError, match='warmup'):
        validate_game_night({**content, 'warmup': ['How are you?', 'Do ' + 'I ' * 12 + '?', 'How was last week?']})


def _model_replies(demo):
    intro = {key: value for key, value in demo.items() if key not in ('games', 'warmup')}
    batches = [
        {'cards': deepcopy(game[level][start:start + 5])}
        for game in demo['games']
        for level in ('elementary', 'advanced')
        for start in range(0, 20, 5)
    ]
    return intro, batches


def test_local_model_uses_topic_in_batches_and_retries_duplicates(monkeypatch):
    demo = generate_game_night('A Night Out')
    intro, batches = _model_replies(demo)
    duplicate = deepcopy(batches[1])
    duplicate['cards'][0]['word'] = batches[0]['cards'][0]['word'].upper()
    answers = iter([intro, batches[0], duplicate, *batches[1:]])
    calls = []
    topic = 'Summer Food Markets'

    def ask(prompt, schema, model, **kwargs):
        assert topic in prompt
        assert model == 'test-model:local'
        calls.append(prompt)
        return next(answers)

    monkeypatch.setattr(ai_content, '_ask_json', ask)
    assert generate_game_night(f' {topic} ', 'test-model:local') == demo
    assert len(calls) == 18
    assert "Taboo targets: repeated 'ticket'" in calls[3]
    assert json.loads(calls[2].splitlines()[-1])['earlier_entries'][0] == 'ticket'


def test_taboo_skips_invalid_candidates_when_enough_unique_cards_remain(monkeypatch):
    demo = generate_game_night('A Night Out')
    intro, batches = _model_replies(demo)
    repeated = deepcopy(batches[0]['cards'][0])
    unusable_clues = {'word': 'passenger', 'forbidden': ['passenger', 'fare', 'ticket']}
    batches[1]['cards'][:0] = [repeated, unusable_clues]
    replies = iter([intro, *batches])
    monkeypatch.setattr(ai_content, '_ask_json', lambda *args, **kwargs: next(replies))
    assert generate_game_night('A Night Out', 'test-model:local') == demo
    assert next(replies, None) is None


def test_local_model_reports_the_failed_stage_without_substituting_demo(monkeypatch):
    demo = generate_game_night('A Night Out')
    intro, _ = _model_replies(demo)
    answers = iter([intro, {'cards': []}, {'cards': []}])
    monkeypatch.setattr(ai_content, '_ask_json', lambda *args, **kwargs: next(answers))
    with pytest.raises(ValueError, match='Taboo elementary, cards 1 to 5.*after 2 attempts'):
        generate_game_night('Summer Food Markets', 'test-model:local')


def test_progress_can_resume_after_an_interrupted_batch(monkeypatch):
    topic, model = 'Summer Food Markets', 'test-model:local'
    demo = generate_game_night(topic)
    intro, batches = _model_replies(demo)
    snapshots = []
    replies = iter([intro, batches[0]])

    def ask_first(*args, **kwargs):
        try:
            return next(replies)
        except StopIteration:
            raise RuntimeError('Connection interrupted.') from None

    def record(completed, total, state):
        snapshots.append((completed, total, state))

    monkeypatch.setattr(ai_content, '_ask_json', ask_first)
    with pytest.raises(RuntimeError, match='Taboo elementary, cards 6 to 10'):
        generate_game_night(topic, model, on_progress=record)
    assert [(done, total) for done, total, _ in snapshots] == [(1, 17), (2, 17)]
    assert snapshots[0][2]['games']['taboo']['elementary'] == []
    saved = json.loads(json.dumps(snapshots[-1][2]))

    remaining = iter(batches[1:])
    monkeypatch.setattr(ai_content, '_ask_json', lambda *args, **kwargs: next(remaining))
    assert generate_game_night(topic, model, resume=saved, on_progress=record) == demo
    assert next(remaining, None) is None
    assert snapshots[-1][:2] == (17, 17)
    assert len(saved['games']['taboo']['elementary']) == 5

    def no_ollama(*args, **kwargs):
        pytest.fail('A complete checkpoint should not ask Ollama to generate anything.')

    monkeypatch.setattr(ai_content, '_ask_json', no_ollama)
    assert generate_game_night(topic, model, resume=snapshots[-1][2]) == demo


@pytest.mark.parametrize('fault', ['incomplete', 'out_of_order', 'duplicate', 'topic', 'model', 'demo'])
def test_resume_rejects_invalid_progress_without_asking_ollama(monkeypatch, fault):
    topic, model = 'Summer Food Markets', 'test-model:local'
    demo = generate_game_night(topic)
    intro, batches = _model_replies(demo)
    saved = {
        'version': 1,
        'topic': topic,
        'model': model,
        'intro': {**intro, 'warmup': demo['warmup']},
        'games': {
            'taboo': {'elementary': batches[0]['cards'], 'advanced': []},
            'problem_solver': {'elementary': [], 'advanced': []},
        },
    }
    if fault == 'incomplete':
        saved['games']['taboo']['elementary'].pop()
    elif fault == 'out_of_order':
        saved['games']['problem_solver']['elementary'] = batches[8]['cards']
    elif fault == 'duplicate':
        saved['games']['taboo']['elementary'][0] = saved['games']['taboo']['elementary'][1]
    elif fault == 'topic':
        topic = 'A Different Topic'
    elif fault == 'model':
        model = 'another-model:local'
    else:
        model = None

    def no_ollama(*args, **kwargs):
        pytest.fail('Invalid checkpoints must be rejected before generation.')

    monkeypatch.setattr(ai_content, '_ask_json', no_ollama)
    with pytest.raises(ValueError):
        generate_game_night(topic, model, resume=saved)


@pytest.mark.parametrize('topic', [None, '   ', 'a' * 111])
def test_rejects_invalid_topic(topic):
    with pytest.raises(ValueError, match='Topic'):
        generate_game_night(topic)
