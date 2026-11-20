from io import BytesIO
import json
from unittest.mock import patch
import pytest
from PIL import Image
from src.ai_content import demo_brief
from src.invitation_content import prepare_invitation,detect_category,PRESETS,BINDINGS
from src.invitation_export import animate_invitation,render_invitation
from src.settings import EventDetails


@pytest.mark.parametrize('category',list(PRESETS))
def test_all_five_reference_concepts_bind_explicit_metadata_offline(category):
    with patch('src.ai_content.urlopen',side_effect=AssertionError('No network in Demo')):
        result=prepare_invitation('Coffee Stories',demo_brief('Coffee Stories'),
                                  EventDetails('My Cafe','21.11.2026','19:30'),category)
    date,venue=BINDINGS[result['slide']]
    assert result['text'][date][:2]==['21.11.26','19:30']
    assert result['text'][venue][0]=='My Cafe'
    assert 'Roastory' not in ' '.join(result['text'][venue])
    assert result['language']=='en'


def test_unknown_event_details_remain_unspecified():
    result=prepare_invitation('Coffee Stories',demo_brief('Coffee Stories'),EventDetails(),'spontaneous')
    date,venue=BINDINGS[result['slide']]
    assert result['text'][date][:2]==['—','—']
    assert result['text'][venue][0]=='—'


def test_local_copy_prompt_excludes_archival_text_and_event_details():
    requests=[]
    def respond(prompt,schema,model,**kwargs):
        requests.append(prompt)
        data=json.loads(prompt.split('/no_think\n')[1])
        result={key:field['draft'] for key,field in data['fields'].items()}
        return result
    with patch('src.ai_content._ask_json',side_effect=respond):
        result=prepare_invitation('Coffee Stories',demo_brief('Coffee Stories'),
                                  EventDetails('Private Cafe','21.11.26','19:30'),'spontaneous','qwen3:8b')
    assert 'Coffee Stories' in ' '.join(text for block in result['text'].values() for text in block)
    assert 'Reality Has a Glitch' not in requests[0]
    for private in ('Private Cafe','21.11.26','19:30'):
        assert private not in requests[0]


def test_model_cannot_pass_by_echoing_an_old_invitation():
    def respond(prompt,schema,model,**kwargs):
        data=json.loads(prompt.split('/no_think\n')[1].split('\nPrevious attempt')[0])
        return {key:field['draft'].replace('Coffee Stories','Other Stories!') for key,field in data['fields'].items()}
    with patch('src.ai_content._ask_json',side_effect=respond) as request:
        result=prepare_invitation('Coffee Stories',demo_brief('Coffee Stories'),EventDetails(),'spontaneous','qwen3:8b')
    body=' '.join(p for block in result['text'].values() for p in block)
    assert 'Coffee Stories' in body and 'Other Stories!' not in body
    assert result['fitted_draft_fields'] and request.call_count==1


def test_location_overflow_is_not_silently_truncated():
    with pytest.raises(ValueError,match='shorter location'):
        prepare_invitation('Coffee Stories',demo_brief('Coffee Stories'),
                           EventDetails('A very long location name that cannot fit in the source'),'spontaneous')


@pytest.mark.parametrize('category',list(PRESETS))
def test_fuller_copy_uses_source_space_and_shows_confirmed_example_location(category):
    from src.invitation_templates import catalog
    result=prepare_invitation('Tiny Decisions',demo_brief('Tiny Decisions'),
                              EventDetails('Holstory Cafe Beşiktaş',time='20:00'),category)
    entry=next(item for item in catalog() if item['slide']==result['slide'])
    schedule,venue=BINDINGS[result['slide']]
    assert result['text'][schedule][1]=='20:00'
    assert ' '.join(result['text'][venue]).strip()=='Holstory Cafe Beşiktaş'
    for shape,paragraphs in entry['blocks'].items():
        if shape in (schedule,venue): continue
        for index,original in enumerate(paragraphs):
            for section in ('Round 1','Round 2'):
                if section.casefold() in original.casefold():
                    assert section in result['text'][shape][index]
            if len(original)>=90:
                assert len(result['text'][shape][index])>=len(original)*.55


def test_ai_tiny_taglines_are_expanded_from_fresh_context_without_layout_changes():
    def respond(prompt,schema,model,**kwargs):
        return {key:'Hi.' for key in schema['required']}
    with patch('src.ai_content._ask_json',side_effect=respond) as request:
        result=prepare_invitation('Tiny Decisions',demo_brief('Tiny Decisions'),EventDetails(),'spontaneous','qwen3:8b')
    assert result['fitted_draft_fields'] and request.call_count==1
    assert len(result['text']['10'][1])>70
    assert 'Tiny Decisions' in result['text']['10'][5]


def test_animation_preserves_proportions_duration_loop_and_readable_hold():
    image=Image.new('RGB',(700,497),'#A976E3')
    from PIL import ImageDraw
    ImageDraw.Draw(image).rectangle((100,100,600,400),fill='white')
    with Image.open(BytesIO(animate_invitation(image))) as gif:
        assert gif.size==image.size and gif.info['loop']==0 and gif.n_frames>1
        durations=[]
        for i in range(gif.n_frames):
            gif.seek(i)
            durations.append(gif.info['duration'])
        assert sum(durations)==8000 and max(durations)>=6000


def test_missing_renderer_reports_error_without_substituting_a_design():
    with patch('src.invitation_export.install_bundled_fonts'), \
         patch('src.invitation_export.libreoffice_executable',side_effect=RuntimeError('LibreOffice missing')):
        with pytest.raises(RuntimeError,match='LibreOffice missing'): render_invitation(b'not used')


@pytest.mark.parametrize('topic,expected',[
    ('Streaming movies','pop_culture'),('Travel traditions','culture_exchange'),
    ('Job interview','business'),('Taboo game night','game_night'),('Everyday surprises','spontaneous')])
def test_demo_topic_routing_uses_five_concepts(topic,expected):
    assert detect_category(topic)==expected
