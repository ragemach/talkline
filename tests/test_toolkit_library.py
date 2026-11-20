from src.toolkit import validate_level, generate_toolkit
from src.toolkit_library import sample_toolkit, lookup_toolkit
from src.toolkit_export import toolkit_html


def test_seed_valid_and_copies_are_independent():
    sample = sample_toolkit()
    for level, data in sample['levels'].items():
        validate_level(data, level)
    sample['levels']['a2']['vocabulary'][0]['turkish'] = 'changed'
    assert lookup_toolkit('Office Boundaries')['a2']['vocabulary'][0]['turkish'] == 'meşgul'
    assert lookup_toolkit('Travel') is None


def test_export_escapes_topic_and_preserves_turkish():
    data = sample_toolkit()
    data['topic'] = '<script>alert(1)</script>'
    html = toolkit_html(data)
    assert '<script>' not in html
    assert 'meşgul' in html
    assert 'charset="utf-8"' in html


def test_seed_generation_locks_meanings_and_grammar(monkeypatch):
    def request(prompt, schema, model, validate):
        return validate({kind: ['This is a complete example.'] * rule['minItems']
                         for kind, rule in schema['properties'].items()})
    monkeypatch.setattr('src.toolkit._validated_request', request)
    monkeypatch.setattr('src.toolkit.review_toolkit', lambda *a: {'summary': 'Fixture', 'issues': []})
    result = generate_toolkit('Office Boundaries')
    assert result['source'] == 'editorial_seed_with_generated_examples'
    seed = sample_toolkit()
    for level in result['levels']:
        assert result['levels'][level]['mini_grammar'] == seed['levels'][level]['mini_grammar']
        for kind in ('vocabulary', 'phrases', 'idioms'):
            for actual, original in zip(result['levels'][level][kind], seed['levels'][level][kind]):
                assert actual['turkish'] == original['turkish']
                assert actual['expression'] == original['expression']
