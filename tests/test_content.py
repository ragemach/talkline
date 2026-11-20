from copy import deepcopy
import json
from unittest.mock import patch

import pytest
from src.ai_content import _validate, demo_brief, create_with_ollama, available_models


def test_demo_is_offline_and_matches_contract():
    with patch('src.ai_content.urlopen', side_effect=AssertionError('network forbidden')):
        data = demo_brief('Unexpected Travel Adventures')
    assert 'Unexpected Travel Adventures' in data['subtitle']
    assert len(data['round1']) == 3 and len(data['game_cards']) == 2


@pytest.mark.parametrize('path,value', [
    (('subtitle',), None), (('tagline',), 12), (('warmup',), 'abc'),
    (('warmup', 0), ' '), (('round1', 0), 'bad card'),
    (('round1', 0, 'a2'), None), (('game_cards', 0, 'patch_a'), ''),
    (('tagline',), 'x' * 241), (('unexpected',), 'extra'),
])
def test_malformed_content_is_rejected(path, value):
    data = deepcopy(demo_brief('Travel'))
    parent = data
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    with pytest.raises(ValueError):
        _validate(data)


def test_duplicate_choices_and_titles_rejected():
    data = demo_brief('Travel')
    data['game_cards'][1]['title'] = data['game_cards'][0]['title'].upper()
    with pytest.raises(ValueError, match='duplicate'):
        _validate(data)
    data = demo_brief('Travel')
    data['game_cards'][0]['patch_b'] = data['game_cards'][0]['patch_a']
    with pytest.raises(ValueError, match='different'):
        _validate(data)


def test_ollama_uses_local_structured_request():
    from io import BytesIO
    reply = json.dumps({'response': json.dumps(demo_brief('Travel'))}).encode()
    with patch('src.ai_content.urlopen', return_value=BytesIO(reply)) as request:
        assert create_with_ollama('Travel')['round1']
    req = request.call_args.args[0]
    assert req.full_url == 'http://127.0.0.1:11434/api/generate'
    payload = json.loads(req.data)
    assert payload['stream'] is False and payload['format']['type'] == 'object'


def test_ollama_unavailable_is_explicit():
    from urllib.error import URLError
    with patch('src.ai_content.urlopen', side_effect=URLError('offline')):
        assert available_models() == []
        with pytest.raises(RuntimeError, match='local Ollama'):
            create_with_ollama('Travel')


def test_bad_json_is_retried_once_and_corrected():
    with patch('src.ai_content._ask_json',side_effect=[ValueError('bad JSON'),demo_brief('Travel')]) as ask:
        assert create_with_ollama('Travel')['subtitle']
    assert ask.call_count==2
    assert 'Previous attempt failed' in ask.call_args.args[0]


def test_retry_limit_prevents_infinite_generation():
    with patch('src.ai_content._ask_json',return_value={}) as ask:
        with pytest.raises(ValueError,match='after 2 attempts'): create_with_ollama('Travel')
    assert ask.call_count==2


def test_review_and_targeted_regeneration_preserve_other_sections():
    from src.ai_content import review_brief, regenerate_section
    brief=demo_brief('Travel')
    original=deepcopy(brief)
    report={'summary':'Game consequences need work.','issues':[{
        'section':'game_cards','severity':'warning','message':'Tighten the causal link.'}]}
    with patch('src.ai_content._ask_json',return_value=report):
        assert review_brief('Travel',brief)==report
    with patch('src.ai_content._ask_json',return_value={'subtitle':'Travel with a twist'}):
        result=regenerate_section('Travel',brief,'subtitle','More playful')
    assert result['subtitle']=='Travel with a twist'
    assert result['game_cards']==original['game_cards']
    assert brief==original


def test_cloud_models_filtered_and_never_requested():
    from io import BytesIO
    reply=json.dumps({'models':[{'name':'qwen3:8b'},{'name':'large:cloud'},
                               {'name':'remote','remote_host':'https://ollama.com'}]}).encode()
    with patch('src.ai_content.urlopen',return_value=BytesIO(reply)):
        assert available_models()==['qwen3:8b']
    with patch('src.ai_content.urlopen') as network:
        with pytest.raises(ValueError): create_with_ollama('Travel',model='large:cloud')
        network.assert_not_called()


def test_semantic_repair_is_bounded_and_reviews_the_new_revision():
    from src.ai_content import repair_reviewed_brief
    brief=demo_brief('Travel')
    changed=deepcopy(brief)
    changed['game_cards'][0]['title']='A repaired card'
    report={'summary':'Repair needed','issues':[
        {'section':'game_cards','severity':'error','message':'Consequence is unrelated.'},
        {'section':'round1','severity':'error','message':'C1 is too shallow.'}]}
    fresh={'summary':'One issue remains','issues':[report['issues'][1]]}
    with patch('src.ai_content.regenerate_section',return_value=changed) as regenerate, \
         patch('src.ai_content.review_brief',return_value=fresh) as review:
        result=repair_reviewed_brief('Travel',brief,report)
    regenerate.assert_called_once()
    assert regenerate.call_args.args[2]=='game_cards'
    assert review.call_args.args[1]==changed
    assert result['review']==fresh and result['content']==changed
    assert brief['game_cards'][0]['title']!='A repaired card'


def test_clean_review_does_not_trigger_extra_generation():
    from src.ai_content import repair_reviewed_brief
    brief=demo_brief('Travel')
    report={'summary':'No critical errors','issues':[]}
    with patch('src.ai_content.regenerate_section') as regenerate:
        result=repair_reviewed_brief('Travel',brief,report)
    regenerate.assert_not_called()
    assert result['repaired_section'] is None
    result['content']['subtitle']='Changed copy'
    assert brief['subtitle']!='Changed copy'


def test_non_reasoning_local_model_falls_back_once():
    from io import BytesIO
    from urllib.error import HTTPError
    from src.ai_content import _ask_json
    error=HTTPError('http://127.0.0.1:11434/api/generate',400,'Bad Request',{},
                    BytesIO(b'{"error":"model does not support thinking"}'))
    response=BytesIO(json.dumps({'response':'{}'}).encode())
    with patch('src.ai_content.urlopen',side_effect=[error,response]) as network:
        assert _ask_json('Return JSON',{'type':'object'},'local-model',think=True)=={}
    assert network.call_count==2
    assert json.loads(network.call_args_list[0].args[0].data)['think'] is True
    assert json.loads(network.call_args_list[1].args[0].data)['think'] is False
