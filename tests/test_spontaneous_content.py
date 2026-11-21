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


def test_local_batches_retry_a_duplicate_before_accepting_new_cards(
    monkeypatch, round_model_cards, round_model_batches,
):
    demo = generate_spontaneous('Coffee shops')
    cards = round_model_cards
    game = demo['game']
    answers = [
        *round_model_batches[0],
        round_model_batches[0][0],  # Invalid second scene batch repeats already accepted scenes.
        *round_model_batches[1],
        *[
            {'cards': game[level][start:start + 5]}
            for level in ('elementary', 'advanced') for start in range(0, 20, 5)
        ],
        {section: demo[section] for section in ('subtitle', 'tagline', 'opening', 'closing')},
    ]
    prompts = []

    def ask(prompt, schema, model, *, think):
        prompts.append(prompt)
        assert model == 'qwen3:8b'
        assert 'Coffee shops' in prompt
        if 'cards' in schema['properties']:
            assert schema['properties']['cards']['maxItems'] == 5
        else:
            assert 'warmup' not in schema['properties']
        return answers.pop(0)

    monkeypatch.setattr(ai_content, '_ask_json', ask)
    actual = generate_spontaneous('Coffee shops', 'qwen3:8b')
    assert {**actual, 'round1': demo['round1']} == demo
    assert len(actual['round1']) == 10
    assert all(actual['round1'][0][tier].startswith(f'{cards[0]["scene"]}. ')
               for tier in ('a2', 'b2', 'c1'))
    assert 'scene' not in actual['round1'][0]
    assert not answers
    assert len(prompts) == 16
    assert 'Previous attempt failed' in prompts[4]
    assert 'duplicate' in prompts[4]


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


@pytest.mark.parametrize('ending', ['', '??'])
def test_local_warmups_ask_for_and_require_one_question_mark(monkeypatch, ending):
    demo = generate_spontaneous('Coffee shops')
    questions = ['How was your week?', 'Do you like tea?', 'How is your day going?']
    answers = [{'warmup': [item[:-1] + ending for item in questions]}, {'warmup': questions}]

    def ask(prompt, schema, model, *, think):
        assert 'each ending with exactly one question mark' in prompt
        return answers.pop(0)

    monkeypatch.setattr(ai_content, '_ask_json', ask)
    revised = regenerate_spontaneous_section('Coffee shops', demo, 'warmup', 'qwen3:8b')
    assert not answers
    assert revised == {**demo, 'warmup': questions}


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


@pytest.mark.parametrize(('tier', 'question', 'reason'), [
    ('a2', 'Would you go there?', 'A2: start with'),
    ('c1', 'What if the price changed?', 'C1: ask a complete question'),
])
def test_new_round_rejects_incomplete_discussion(monkeypatch, round_model_batches, tier, question, reason):
    demo = generate_spontaneous('Coffee shops')
    scenes, questions, _ = deepcopy(round_model_batches[0])
    questions['cards'][0][tier] = question
    answers = iter((scenes, questions, questions))
    monkeypatch.setattr(ai_content, '_ask_json', lambda *args, **kw: next(answers))
    with pytest.raises(ValueError, match=reason):
        regenerate_spontaneous_section('Coffee shops', demo, 'round1', 'qwen3:8b')


@pytest.mark.parametrize('private_question,public_question', [
    ('What is your current remote pay rate?', 'What salary would you offer a new worker?'),
    ('How much do you get paid per shift?', 'How would you ask about pay at an interview?'),
    ('What’s your hourly rate?', 'What is your salary negotiation strategy?'),
    ('How much do you earn at work?', 'What is your pay in this role-play?'),
])
def test_generation_retries_private_pay_without_rejecting_pay_as_a_topic(
    monkeypatch, round_model_batches, private_question, public_question,
):
    topic = 'Pay at a coffee shop'
    original = generate_spontaneous(topic)
    scenes, questions, approved = deepcopy(round_model_batches[0])
    rejected = deepcopy(questions)
    rejected['cards'][0]['a2'] = private_question
    questions['cards'][0]['a2'] = public_question
    replies = [scenes, rejected, questions, approved, *round_model_batches[1]]
    prompts = []

    def respond(prompt, *args, **kwargs):
        prompts.append(prompt)
        return replies.pop(0)

    monkeypatch.setattr(ai_content, '_ask_json', respond)
    revised = regenerate_spontaneous_section(topic, original, 'round1', 'qwen3:8b')
    assert revised['round1'][0]['a2'].endswith(public_question)
    assert 'personal earnings' in prompts[2]
    assert not replies
    # Older sessions must still open so the host can edit an earlier question.
    original['round1'][0]['a2'] = private_question
    assert validate_spontaneous(original) is original


def test_review_repairs_only_the_flagged_cards(monkeypatch, round_model_cards, round_model_batches, round_review):
    topic = 'A neighbourhood coffee shop open every day'
    original = generate_spontaneous(topic)
    before = deepcopy(original)
    scenes, questions, _ = round_model_batches[1]
    review = round_review(5, {
        2: ('only accepts cards', 'The C1 question changes the payment situation to card-only.'),
        5: ('closes on Sundays', 'Closing on Sundays contradicts the seven-day opening schedule.'),
    })
    cash = dict(round_model_cards[6], c1='Who should cover the cost of giving cash customers change?')
    sunday = dict(round_model_cards[9], title='Sunday Staff', scene='Two staff members open the shop on Sunday',
                  b2='Which Sunday shift would you prefer and why?')
    answers = [*round_model_batches[0], scenes, questions, review, {'cards': [cash, sunday]}, round_review(2)]
    writing_prompts = []

    def respond(prompt, schema, *args, **kwargs):
        fields = schema['properties'].get('cards', {}).get('items', {}).get('properties', {})
        if 'a2' in fields:
            writing_prompts.append(prompt)
        return answers.pop(0)

    monkeypatch.setattr(ai_content, '_ask_json', respond)

    revised = regenerate_spontaneous_section(topic, original, 'round1', 'qwen3:8b')

    expected_cards = [*round_model_cards[:6], cash, *round_model_cards[7:9], sunday]
    for actual, expected in zip(revised['round1'], expected_cards, strict=True):
        assert actual == {
            'title': expected['title'],
            **{tier: f'{expected["scene"]}. {expected[tier]}' for tier in ('a2', 'b2', 'c1')},
        }
    assert {**revised, 'round1': original['round1']} == before
    assert original == before
    assert not answers
    assert len(writing_prompts) == 3  # Two fresh batches and their one repair.
    for prompt in writing_prompts:
        assert 'fictional amounts' in prompt
        assert 'What childhood game would you hate to forget?' not in prompt
        assert 'Who loses the most when memories are traded?' not in prompt
        assert 'When is it fair to trade memories if some lose their most precious ones?' not in prompt


def test_unresolved_contradiction_preserves_last_reviewed_batch(
    monkeypatch, round_model_cards, round_model_batches, round_review,
):
    topic = 'A neighbourhood coffee shop open every day'
    issue = ('closes on Sundays', 'The shop still closes on Sundays despite opening every day.')
    scenes, questions, _ = round_model_batches[1]
    attempted = dict(round_model_cards[9], title='Closed on Sundays')
    answers = [*round_model_batches[0], scenes, questions, round_review(5, {5: issue}),
               {'cards': [attempted]}, round_review(1, {1: issue})]
    monkeypatch.setattr(ai_content, '_ask_json', lambda *args, **kwargs: answers.pop(0))
    checkpoints = []

    with pytest.raises(ValueError, match=r'(?is)Round 1.*10.*closes on Sundays'):
        generate_spontaneous(topic, 'qwen3:8b',
                             on_progress=lambda completed, total, state: checkpoints.append(state))

    assert not answers
    assert len(checkpoints) == 1
    assert [card['title'] for card in checkpoints[0]['round1']] == [c['title'] for c in round_model_cards[:5]]
    assert checkpoints[0]['game'] == {'elementary': [], 'advanced': []}


@pytest.mark.parametrize('problem', ['out of range', 'omitted', 'duplicate'])
def test_review_must_address_every_card_once(monkeypatch, round_model_batches, round_review, problem):
    topic = 'Coffee shops'
    draft = generate_spontaneous(topic)
    before = deepcopy(draft)
    scenes, questions, _ = round_model_batches[0]
    invalid = round_review(5)
    if problem == 'omitted':
        invalid['checks'].pop()
    else:
        invalid['checks'][0]['card'] = 0 if problem == 'out of range' else 2
    answers = [scenes, questions, invalid, invalid]
    monkeypatch.setattr(ai_content, '_ask_json', lambda *args, **kwargs: answers.pop(0))

    with pytest.raises(ValueError, match='after 2 attempts'):
        regenerate_spontaneous_section(topic, draft, 'round1', 'qwen3:8b')
    assert not answers
    assert draft == before


def test_a_revision_must_quote_the_card_it_flags(monkeypatch, round_model_batches, round_review):
    topic = 'Coffee shops'
    before = generate_spontaneous(topic)
    scenes, questions, accepted = round_model_batches[0]
    misplaced = round_review(5, {1: ('small table', 'The early opening says nothing about seating.')})
    assert 'small table' in scenes['cards'][1]['scene']
    answers = [scenes, questions, misplaced, accepted, *round_model_batches[1]]
    monkeypatch.setattr(ai_content, '_ask_json', lambda *args, **kwargs: answers.pop(0))

    revised = regenerate_spontaneous_section(topic, before, 'round1', 'qwen3:8b')

    assert not answers
    assert revised['round1'][0]['title'] == scenes['cards'][0]['title']


@pytest.mark.parametrize('invalid_topic', [None, '   ', 'x' * 111])
def test_invalid_topic_is_rejected_before_generation(invalid_topic):
    with pytest.raises(ValueError, match='Topic'):
        generate_spontaneous(invalid_topic)


def test_full_validation_rejects_same_question_at_multiple_levels():
    draft = generate_spontaneous('Coffee shops')
    draft['round1'][0]['b2'] = draft['round1'][0]['a2']
    with pytest.raises(ValueError, match='Round 1 questions.*duplicate'):
        validate_spontaneous(draft)


def test_resume_retains_valid_batches_after_a_connection_failure(monkeypatch, round_model_batches):
    topic = 'Coffee shops'
    model = 'qwen3:8b'
    demo = generate_spontaneous(topic)
    game = demo['game']
    first_answers = [*round_model_batches[0], *round_model_batches[1],
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
        {section: demo[section] for section in ('subtitle', 'tagline', 'opening', 'closing')},
    ]
    monkeypatch.setattr(ai_content, '_ask_json', lambda *args, **kwargs: remaining_answers.pop(0))
    resumed = generate_spontaneous(topic, model, resume=checkpoint, on_progress=report)
    assert not remaining_answers
    assert {**resumed, 'round1': demo['round1']} == demo
    assert resumed['round1'] == checkpoint['round1']
    assert len(checkpoint['game']['elementary']) == 5
    assert snapshots[-1][0] == 11
    assert generate_spontaneous(topic, model, resume=snapshots[-1][1]) == resumed
    older_checkpoint = {**snapshots[-1][1], 'round1': demo['round1']}
    assert generate_spontaneous(topic, model, resume=older_checkpoint) == demo
    with pytest.raises(ValueError, match='topic:'):
        generate_spontaneous('Beach holidays', model, resume=checkpoint)
