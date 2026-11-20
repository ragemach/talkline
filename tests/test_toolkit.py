import pytest
from src.toolkit import generate_toolkit, validate_level


def material():
    def entry(word):
        return {'expression': word, 'turkish': 'anlam', 'example': f'I use {word} every day.'}
    return {'vocabulary': [entry(word) for word in ('budget','salary','cost','price','save','spend','bill','income')],
            'phrases': [entry(word) for word in ('save money','pay the bill','keep a budget')], 'idioms': [entry('break the bank')],
            'mini_grammar': {'title': 'Should', 'explanation': 'Use should for advice.',
                             'pattern': 'should + verb',
                             'examples': ['You should save money.', 'We should plan ahead.']}}


def test_generator_requests_each_level_and_retains_topic(monkeypatch):
    calls = []
    def request(prompt, schema, model, validate):
        calls.append(prompt)
        data = material()
        if 'level a2.' in prompt:
            data['idioms'] = []
        return validate(data)
    monkeypatch.setattr('src.toolkit._validated_request', request)
    monkeypatch.setattr('src.toolkit.review_toolkit', lambda *args: {'summary': 'Review fixture', 'issues': []})
    result = generate_toolkit('Office budgets')
    assert list(result['levels']) == ['a2', 'b1', 'b2_c1']
    assert all('Office budgets' in prompt for prompt in calls)
    assert result['review_status'] == 'local_review_complete'


@pytest.mark.parametrize('fault', ['translation', 'sentence', 'duplicate', 'idiom', 'grammar'])
def test_incomplete_toolkit_rejected(fault):
    data = material()
    if fault == 'translation':
        data['vocabulary'][0]['turkish'] = ''
    elif fault == 'sentence':
        data['vocabulary'][0]['example'] = 'Budget...'
    elif fault == 'duplicate':
        data['phrases'][0]['expression'] = 'Budget!'
    elif fault == 'idiom':
        data['idioms'] = []
    else:
        data['mini_grammar']['examples'] = ['Only one example.']
    with pytest.raises(ValueError):
        validate_level(data, 'b2_c1')


def test_a2_can_omit_idioms():
    data = material()
    data['idioms'] = []
    validate_level(data, 'a2')


@pytest.mark.parametrize('count', [2, 6, 11])
def test_vocabulary_count_outside_seven_to_ten_rejected(count):
    data = material()
    data['vocabulary'] = [dict(data['vocabulary'][0], expression=f'word {i}') for i in range(count)]
    with pytest.raises(ValueError):
        validate_level(data, 'b1')


def test_review_failure_keeps_content_but_never_claims_success(monkeypatch):
    def request(prompt, schema, model, validate):
        data = material()
        if 'level a2.' in prompt:
            data['idioms'] = []
        return validate(data)
    def fail(*args):
        raise RuntimeError('Ollama unavailable')
    monkeypatch.setattr('src.toolkit._validated_request', request)
    monkeypatch.setattr('src.toolkit.review_toolkit', fail)
    result = generate_toolkit('Travel')
    assert result['review_status'] == 'local_review_failed'
    assert result['review_error'] == 'Ollama unavailable'
    assert len(result['levels']) == 3
