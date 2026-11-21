from io import BytesIO
import json
from pathlib import Path
from unittest.mock import patch
import zipfile
import pytest
from streamlit.testing.v1 import AppTest
from src.settings import load_settings, save_settings, UserSettings

APP = Path(__file__).resolve().parents[1] / 'app.py'


def test_toolkit_export_runs_offline_and_hides_stale_topic():
    from src.toolkit_library import sample_toolkit
    from pptx import Presentation
    with patch('src.ai_content.urlopen', side_effect=AssertionError('Export must be offline')):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.text_input(key='topic_input').set_value('Office Boundaries')
        app.session_state['toolkit'] = sample_toolkit()
        app.run()
        app.button(key='build_toolkit_pptx').click().run()
        assert not app.exception and not app.error
        deck = Presentation(BytesIO(app.session_state['toolkit_deck']))
        assert len(deck.slides) == 7
        assert any('A1/A2' in heading.value for heading in app.subheader)
        app.text_input(key='topic_input').set_value('A different topic').run()
        assert 'build_toolkit_pptx' not in [button.key for button in app.button]


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    path=tmp_path/'settings.json'
    with patch('src.settings.load_settings',side_effect=lambda:load_settings(path)), \
         patch('src.settings.save_settings',side_effect=lambda settings:save_settings(settings,path)), \
         patch('src.ai_content.available_models', return_value=[]), \
         patch('src.run_store.RUN_PATH', tmp_path/'last_run.zip'), \
         patch('src.checkpoints.SPONTANEOUS_PROGRESS_PATH', tmp_path/'spontaneous-progress.json'), \
         patch('src.checkpoints.GAME_NIGHT_PROGRESS_PATH', tmp_path/'game-night-progress.json'), \
         patch('src.checkpoints.BUSINESS_PROGRESS_PATH', tmp_path/'business-progress.json'):
        yield path


@pytest.fixture
def prepared_local_ai(monkeypatch):
    """Replace model responses only so the tests can exercise real local exports."""
    from src.ai_content import demo_brief
    from src.business_content import generate_business
    from src.game_night_content import generate_game_night
    from src.invitation_content import detect_category, prepare_invitation
    from src.spontaneous_content import generate_spontaneous
    from src.spontaneous_demo_toolkit import demo_spontaneous_toolkit

    monkeypatch.setattr('src.ai_content.available_models', lambda: ['qwen3:8b'])
    monkeypatch.setattr('src.ai_content.create_with_ollama', lambda topic, model: demo_brief(topic))
    monkeypatch.setattr('src.ai_content.review_brief', lambda *args, **kwargs: {'summary': 'Reviewed', 'issues': []})
    monkeypatch.setattr('src.spontaneous_content.generate_spontaneous',
                        lambda topic, model, **kwargs: generate_spontaneous(topic))
    monkeypatch.setattr('src.business_content.generate_business',
                        lambda topic, model, **kwargs: generate_business(topic))
    monkeypatch.setattr('src.game_night_content.generate_game_night',
                        lambda topic, model, **kwargs: generate_game_night(topic))
    monkeypatch.setattr('src.toolkit.generate_toolkit',
                        lambda topic, model: dict(demo_spontaneous_toolkit(topic), model=model))
    monkeypatch.setattr('src.invitation_content.detect_category', lambda topic, model: detect_category(topic))
    monkeypatch.setattr('src.session_export.prepare_invitation',
                        lambda topic, brief, event, category, model: prepare_invitation(topic, brief, event, category))


def test_local_ui_exports_real_zip_and_preserves_previous_run(prepared_local_ai):
    with patch('src.ai_content.urlopen', side_effect=AssertionError('Model replies are provided by the test')):
        app = AppTest.from_file(str(APP), default_timeout=60).run()
        assert not app.exception
        assert not app.radio
        assert app.selectbox(key='concept_input').value == 'auto'
        assert [field.value for field in app.text_input] == ['', '', '', '']
        assert app.button(key='generate').disabled
        app.text_input[0].set_value('Unexpected Travel Adventures')
        app.selectbox(key='concept_input').set_value('culture_exchange').run()
        app.button(key='generate').click().run()
        assert not app.exception
        app.button(key='build').click().run(timeout=60)
        assert not app.exception and not app.error
        with zipfile.ZipFile(BytesIO(app.session_state['package'])) as archive:
            assert archive.testzip() is None
            assert set(archive.namelist()) == {'TalkLine_Prototype.pptx', 'TalkLine_Invitation.gif', 'TalkLine_Invitation.pptx', 'TalkLine_Invitation.png', 'TalkLine_Game.html', 'TalkLine_Host_Guide.html', 'content.json'}
            game = archive.read('TalkLine_Game.html').decode()
            assert 'The Queue That Moves' in game
            from pptx import Presentation
            deck = Presentation(BytesIO(archive.read('TalkLine_Prototype.pptx')))
            assert any(run.hyperlink.address == 'TalkLine_Game.html'
                       for shape in deck.slides[-1].shapes if shape.has_text_frame
                       for paragraph in shape.text_frame.paragraphs for run in paragraph.runs)
            data = json.loads(archive.read('content.json'))
            assert data['topic'] == 'Unexpected Travel Adventures'
            assert data['invitation']['category'] == 'culture_exchange'
            assert data['engine']['model'] == 'qwen3:8b'
            assert data['event'] == {'venue': '', 'date': '', 'time': ''}
            titles = [stage['title'] for stage in data['session_sequence']]
            assert titles == ['Welcome', 'Warm-up', 'Round 1: Discussion', 'Break',
                              'Round 2: Patch Notes', 'Cooldown', 'Rate Us and thank everyone']
            guide = archive.read('TalkLine_Host_Guide.html').decode()
            assert 'href="TalkLine_Game.html"' in guide
            assert 'TalkLine_Toolkit.html' not in guide

        # Adding a Toolkit for the current topic invalidates the earlier ZIP.
        from src.toolkit_library import sample_toolkit
        toolkit = sample_toolkit()
        toolkit['topic'] = 'Unexpected Travel Adventures'
        app.session_state['toolkit'] = toolkit
        app.run()
        assert any('saved files are for an earlier version' in alert.value for alert in app.info)
        assert not any('prototype ZIP' in button.label
                       for button in app.get('download_button'))
        app.button(key='build').click().run(timeout=60)
        assert not app.exception and not app.error
        with zipfile.ZipFile(BytesIO(app.session_state['package'])) as archive:
            guide = archive.read('TalkLine_Host_Guide.html').decode()
            assert guide.index('<h2>Toolkit</h2>') < guide.index('<h2>Mini grammar</h2>')
            assert guide.index('<h2>Mini grammar</h2>') < guide.index('<h2>Round 1: Discussion</h2>')
            assert 'href="TalkLine_Toolkit.pptx"' in guide
            assert 'href="TalkLine_Toolkit.html"' in guide
            assert 'https://docs.google.com/forms/' in guide
            assert 'walk on eggshells' in archive.read('TalkLine_Toolkit.html').decode()
            assert 'TalkLine_Toolkit.pptx' in archive.namelist()
        good_zip = app.session_state['package']
        reopened = AppTest.from_file(str(APP), default_timeout=60).run()
        assert not reopened.exception and not reopened.error
        assert reopened.text_input(key='topic_input').value == 'Unexpected Travel Adventures'
        assert reopened.session_state['package'] == good_zip
        assert any('prototype ZIP' in button.label for button in reopened.get('download_button'))

        # A failed replacement preserves the successful run but hides its files
        # while the form shows a different event.
        reopened.text_input(key='topic_input').set_value('Unfinished replacement travel traditions').run()
        assert reopened.selectbox(key='concept_input').value == 'auto'
        with patch('src.ai_content.create_with_ollama', side_effect=ValueError('invalid content')):
            reopened.button(key='generate').click().run()
        assert reopened.error
        assert reopened.session_state['package'] == good_zip
        assert reopened.session_state['metadata']['topic'] == 'Unexpected Travel Adventures'
        assert reopened.button(key='build').disabled
        assert not any('prototype ZIP' in button.label for button in reopened.get('download_button'))
        reopened.button(key='load_saved_inputs').click().run()
        assert not reopened.button(key='build').disabled
        assert any('prototype ZIP' in button.label for button in reopened.get('download_button'))
        reopened.text_input(key='venue_input').set_value('A different venue').run()
        assert reopened.button(key='build').disabled
        assert not any('prototype ZIP' in button.label for button in reopened.get('download_button'))
        reopened.button(key='load_saved_inputs').click().run()
        with patch('src.invitation_export.render_invitation', side_effect=RuntimeError('renderer failed')):
            reopened.button(key='build').click().run()
        assert reopened.error
        assert reopened.session_state['package'] == good_zip
        fresh = AppTest.from_file(str(APP), default_timeout=60).run()
        assert not fresh.exception
        assert fresh.session_state['package'] == good_zip

        # Earlier releases stored only 'auto' when the invitation style was automatic.
        from src.run_state import export_revision
        from src.run_store import load_run, save_run
        saved = load_run()
        saved.draft['metadata'].pop('concept_selection', None)
        saved.draft['metadata']['concept'] = 'auto'
        save_run(saved.draft, package=good_zip, export_revision=export_revision(saved.draft))
        with patch('src.ai_content.available_models', return_value=[]):
            legacy = AppTest.from_file(str(APP)).run()
            assert not legacy.exception and not legacy.error
            assert legacy.session_state['package'] == good_zip
            assert any('prototype ZIP' in button.label for button in legacy.get('download_button'))


def test_resume_local_draft_without_ollama_or_export():
    from src.business_content import generate_business
    from src.toolkit_library import sample_toolkit

    draft = generate_business('A local topic')
    toolkit = dict(sample_toolkit(), topic='A local topic')
    with patch('src.ai_content.available_models', return_value=['qwen3:8b']), \
         patch('src.toolkit.generate_toolkit', return_value=toolkit), \
         patch('src.business_content.generate_business', return_value=draft):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.text_input(key='topic_input').set_value('A local topic')
        app.text_input(key='venue_input').set_value('Office')
        app.text_input(key='time_input').set_value('20:15')
        app.selectbox(key='concept_input').set_value('business').run()
        app.button(key='generate').click().run()
        assert not app.exception and not app.error

    with patch('src.ai_content.available_models', return_value=[]), \
         patch('src.business_content.generate_business', side_effect=AssertionError('Resume cannot rerun generation')):
        reopened = AppTest.from_file(str(APP), default_timeout=30).run()
        assert not reopened.exception and not reopened.error
        assert reopened.session_state['brief'] == draft
        assert reopened.text_input(key='topic_input').value == 'A local topic'
        assert reopened.text_input(key='venue_input').value == 'Office'
        assert reopened.text_input(key='time_input').value == '20:15'
        assert reopened.selectbox(key='concept_input').value == 'business'
        assert reopened.button(key='generate').disabled
        assert 'package' not in reopened.session_state


def test_unrelated_toolkit_preserves_saved_event_revision():
    from src.ai_content import demo_brief
    from src.run_state import DEMO_MODE, draft_from_state, export_revision, set_toolkit
    from src.toolkit_library import sample_toolkit

    state = {
        'metadata': {'topic': 'Office Boundaries', 'mode': DEMO_MODE, 'model': None,
                     'venue': '', 'date': '', 'time': '', 'concept': 'business'},
        'brief': demo_brief('Office Boundaries'),
        'toolkit': sample_toolkit(),
    }
    original_revision = export_revision(draft_from_state(state))
    set_toolkit(state, dict(sample_toolkit(), topic='Another topic'))
    assert export_revision(draft_from_state(state)) == original_revision
    revised = sample_toolkit()
    revised['levels']['a2']['vocabulary'][0]['example'] = 'I am busy this afternoon.'
    set_toolkit(state, revised)
    assert export_revision(draft_from_state(state)) != original_revision


def test_saved_defaults_reload_in_a_new_session(isolated_settings):
    app=AppTest.from_file(str(APP)).run()
    app.text_input(key='venue_input').set_value('My venue')
    app.text_input(key='time_input').set_value('19:30')
    app.button(key='save_defaults').click().run()
    assert load_settings(isolated_settings).event.venue == 'My venue'
    fresh=AppTest.from_file(str(APP)).run()
    assert fresh.text_input(key='venue_input').value == 'My venue'
    assert fresh.text_input(key='date_input').value == ''
    assert fresh.text_input(key='time_input').value == '19:30'


def test_spontaneous_exports_and_edits_full_offline_session(prepared_local_ai):
    from html.parser import HTMLParser
    from pptx import Presentation

    class PackageLinks(HTMLParser):
        def __init__(self):
            super().__init__()
            self.targets = []

        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                self.targets.append(dict(attrs)['href'])

    with patch('src.ai_content.urlopen', side_effect=AssertionError('Model replies are provided by the test')):
        app = AppTest.from_file(str(APP), default_timeout=90).run()
        app.text_input(key='topic_input').set_value('Reality Has a Glitch!')
        app.selectbox(key='concept_input').set_value('spontaneous').run()
        app.button(key='generate').click().run()
        assert not app.exception and not app.error
        assert any(section.label == 'Round 1 discussion cards' for section in app.get('expander'))
        app.button(key='build').click().run()
        assert not app.exception and not app.error, [error.value for error in app.error]
        package = app.session_state['package']
        with zipfile.ZipFile(BytesIO(package)) as kit:
            assert kit.testzip() is None
            assert {'TalkLine_Presentation.pptx', 'TalkLine_Game.html', 'TalkLine_Invitation.gif',
                    'TalkLine_Toolkit.html', 'TalkLine_Host_Guide.html'} <= set(kit.namelist())
            loaded = json.loads(kit.read('content.json'))
            brief = loaded['content']
            assert len(brief['round1']) == 10
            assert all(len(brief['game'][level]) == 20 for level in ('elementary', 'advanced'))
            guide = kit.read('TalkLine_Host_Guide.html').decode('utf-8')
            links = PackageLinks()
            links.feed(guide)
            assert all(target in kit.namelist() for target in links.targets if not target.startswith('https://'))
            deck = Presentation(BytesIO(kit.read('TalkLine_Presentation.pptx')))
            assert len(deck.slides) >= 23
            assert all(slide.has_notes_slide for slide in deck.slides)

        resumed = AppTest.from_file(str(APP), default_timeout=90).run()
        assert not resumed.exception
        assert resumed.session_state['package'] == package
        resumed.selectbox(key='edit_session_part').set_value('Wrap-up').run()
        closing = next(field for field in resumed.text_area if field.label == 'Closing paragraph')
        closing.set_value('Share one thing you would change after our conversation today.')
        save = next(button for button in resumed.button if button.label == 'Save wrap-up')
        save.click().run()
        assert not resumed.exception and not resumed.error
        assert 'package' not in resumed.session_state
        fresh = AppTest.from_file(str(APP), default_timeout=90).run()
        assert fresh.session_state['brief']['closing'] == 'Share one thing you would change after our conversation today.'
        assert fresh.session_state['brief']['game'] == brief['game']


def test_long_discussion_edits_survive_reopen_and_export(prepared_local_ai):
    from html import unescape
    from pptx import Presentation
    from src.content_rules import ROUND_CARD_TEXT_LIMITS
    from src.run_state import LOCAL_MODE
    from src.run_store import save_run
    from src.session_sequence import FULL_SPONTANEOUS
    from src.spontaneous_content import generate_spontaneous
    from src.spontaneous_demo_toolkit import demo_spontaneous_toolkit
    from src.template_blueprints import text_shapes

    topic = 'What if people could trade one memory each year?'
    scene = 'An old man gains his daughter’s college graduation memory. '
    draft = generate_spontaneous(topic, model=None)
    card = draft['round1'][1]
    card['title'] = 'Happy Memories'
    card['a2'] = scene + 'Where would you go to relive your favorite childhood memory?'
    save_run({'metadata': {'topic': topic, 'venue': '', 'date': '', 'time': '', 'concept': 'spontaneous',
                           'workflow': FULL_SPONTANEOUS, 'mode': LOCAL_MODE, 'model': 'qwen3:8b'},
              'brief': draft, 'toolkit': demo_spontaneous_toolkit(topic)})
    edits = {
        'a2': scene + 'Which day with your family or friends would you most like to remember when you are older?',
        'b2': scene + 'Why do families remember the same day in different ways, and what gets lost when someone else remembers it for them?',
        'c1': scene + 'How should families weigh the comfort of sharing an important day against a person’s right to keep a private memory?',
    }
    app = AppTest.from_file(str(APP), default_timeout=90).run()
    app.selectbox(key='edit_session_part').set_value('Round 1 question').run()
    next(box for box in app.selectbox if box.label == 'Discussion card').set_value(1).run()
    for tier, value in edits.items():
        field = next(field for field in app.text_area if field.label == f'{tier.upper()} question')
        assert field.proto.max_chars == ROUND_CARD_TEXT_LIMITS[tier]
        assert field.value == card[tier]
        assert (115 if tier == 'a2' else 165) < len(value) <= field.proto.max_chars
        field.set_value(value)
    next(button for button in app.button if button.label == 'Save question').click().run()
    assert not app.error and not app.exception

    reopened = AppTest.from_file(str(APP), default_timeout=90).run()
    assert reopened.session_state['brief']['round1'][1] == {**card, **edits}
    reopened.button(key='build').click().run()
    assert not reopened.error and not reopened.exception
    with zipfile.ZipFile(BytesIO(reopened.session_state['package'])) as archive:
        content = json.loads(archive.read('content.json'))['content']
        assert content['round1'][1] == {**card, **edits}
        guide = unescape(archive.read('TalkLine_Host_Guide.html').decode('utf-8'))
        deck = Presentation(BytesIO(archive.read('TalkLine_Presentation.pptx')))
        for slide in deck.slides:
            texts = [shape.text for _, shape in text_shapes(slide.shapes)]
            if card['title'] in texts:
                break
        else:
            pytest.fail('The edited discussion slide is missing.')
        for value in edits.values():
            assert value in texts and value in slide.notes_slide.notes_text_frame.text
            assert value in guide


def test_game_night_exports_and_recovers_both_offline_games(prepared_local_ai):
    from pptx import Presentation
    from src.session_sequence import FULL_GAME_NIGHT, GAME_NIGHT_FILES

    with patch('src.ai_content.urlopen', side_effect=AssertionError('Model replies are provided by the test')), \
         patch('src.invitation_content.detect_category', return_value='business') as classify:
        app = AppTest.from_file(str(APP), default_timeout=90).run()
        app.text_input(key='topic_input').set_value('A Night of Team Challenges').run()
        assert 'Business English' in app.button(key='generate').label
        app.selectbox(key='concept_input').set_value('game_night').run()
        assert 'Game Night' in app.button(key='generate').label
        app.button(key='generate').click().run()
        assert not app.exception and not app.error, [error.value for error in app.error]
        app.button(key='build').click().run()
        assert not app.exception and not app.error, [error.value for error in app.error]
        package = app.session_state['package']
        with zipfile.ZipFile(BytesIO(package)) as kit:
            assert kit.testzip() is None
            payload = json.loads(kit.read('content.json'))
            assert payload['stage'] == FULL_GAME_NIGHT
            assert payload['invitation']['category'] == 'game_night'
            assert [game['mechanic'] for game in payload['content']['games']] == ['taboo', 'problem_solver']
            assert all(len(game[level]) == 20 for game in payload['content']['games']
                       for level in ('elementary', 'advanced'))
            invitation = ' '.join(line for block in payload['invitation']['text'].values() for line in block)
            assert 'A Night of Team Challenges' in invitation
            assert 'Round 1: Play Taboo.' in invitation and 'Round 2: Play Problem Solver.' in invitation
            guide = kit.read('TalkLine_Host_Guide.html').decode('utf-8')
            assert guide.index('Round 1: Taboo') < guide.index('Break') < guide.index('Round 2: Problem Solver')
            deck = Presentation(BytesIO(kit.read('TalkLine_Presentation.pptx')))
            links = {rel.target_ref for slide in deck.slides for rel in slide.part.rels.values() if rel.is_external}
            for filename in GAME_NIGHT_FILES:
                assert f'href="{filename}"' in guide and filename in links
                assert kit.read(filename).startswith(b'<!')
            assert 'TalkLine_Invitation.gif' in kit.namelist()
            assert 'TalkLine_Game.html' not in kit.namelist()

        reopened = AppTest.from_file(str(APP), default_timeout=90).run()
        assert not reopened.exception and not reopened.error
        assert reopened.selectbox(key='concept_input').value == 'game_night'
        classify.assert_called_once()
        assert reopened.session_state['package'] == package
        reopened.selectbox(key='edit_session_part').set_value('Round 1 game card').run()
        target = next(field for field in reopened.text_input if field.label == 'Target word')
        target.set_value('Concert ticket')
        next(button for button in reopened.button if button.label == 'Save game card').click().run()
        assert not reopened.exception and not reopened.error
        assert 'package' not in reopened.session_state
        assert reopened.session_state['brief']['games'][0]['elementary'][0]['word'] == 'Concert ticket'
        assert reopened.session_state['brief']['games'][1] == payload['content']['games'][1]
        reopened.text_input(key='topic_input').set_value('Presenting a budget').run()
        assert reopened.selectbox(key='concept_input').value == 'auto'
        assert 'Business English' in reopened.button(key='generate').label
        assert classify.call_count == 2
        assert reopened.button(key='build').disabled


def test_automatic_business_concept_drives_deck_game_invitation_and_saved_run(prepared_local_ai):
    from pptx import Presentation
    from src.session_sequence import BUSINESS_GAME_FILE, FULL_BUSINESS

    topic = 'Business Beyond the Office'
    with patch('src.ai_content.urlopen', side_effect=AssertionError('Model replies are provided by the test')), \
         patch('src.invitation_content.detect_category', return_value='business') as classify, \
         patch('src.session_export.detect_category', side_effect=AssertionError('Export must use the saved concept')):
        app = AppTest.from_file(str(APP), default_timeout=90).run()
        classify.assert_not_called()
        app.text_input(key='topic_input').set_value(topic).run()
        assert 'Business English' in app.button(key='generate').label
        app.text_input(key='time_input').set_value('20:00').run()
        classify.assert_called_once_with(topic, 'qwen3:8b')
        app.button(key='generate').click().run()
        assert app.session_state['metadata']['concept'] == 'business'
        assert app.session_state['metadata']['concept_selection'] == 'auto'
        app.button(key='build').click().run()
        assert not app.exception and not app.error, [error.value for error in app.error]
        with zipfile.ZipFile(BytesIO(app.session_state['package'])) as kit:
            payload = json.loads(kit.read('content.json'))
            assert payload['stage'] == FULL_BUSINESS
            assert payload['invitation']['category'] == 'business'
            assert payload['content']['game']['mechanic'] == 'smart_or_sneaky'
            assert len(payload['content']['round1']) == 10
            assert len(payload['content']['game']['advanced']) == 20
            guide = kit.read('TalkLine_Host_Guide.html').decode()
            deck = Presentation(BytesIO(kit.read('TalkLine_Presentation.pptx')))
            assert f'href="{BUSINESS_GAME_FILE}"' in guide
            assert any(rel.target_ref == BUSINESS_GAME_FILE for slide in deck.slides
                       for rel in slide.part.rels.values() if rel.is_external)
            assert BUSINESS_GAME_FILE in kit.namelist()
        classify.assert_called_once()

        with patch('src.ai_content.available_models', return_value=[]):
            reopened = AppTest.from_file(str(APP)).run()
            assert not reopened.exception and not reopened.error
            assert reopened.selectbox(key='concept_input').value == 'auto'
            assert reopened.button(key='generate').disabled
            assert reopened.session_state['package'] == app.session_state['package']
            assert any(button.label == 'Download PowerPoint' for button in reopened.get('download_button'))
        with patch('src.ai_content.available_models', return_value=['another-local-model']):
            reopened = AppTest.from_file(str(APP)).run()
            assert not reopened.error and not reopened.exception
            assert reopened.button(key='generate').label == 'Generate Business English session'
            assert any(button.label == 'Download PowerPoint' for button in reopened.get('download_button'))
        classify.assert_called_once()


def test_spontaneous_generation_resumes_after_local_connection_failure():
    from src.spontaneous_content import generate_spontaneous
    from src.spontaneous_demo_toolkit import demo_spontaneous_toolkit

    topic = 'What if buses ran all night?'
    sample = generate_spontaneous(topic)
    saved_batch = {'version': 1, 'topic': topic, 'model': 'qwen3:8b',
                   'round1': sample['round1'][:5],
                   'game': {'elementary': [], 'advanced': []}, 'intro': None}
    completed = {**saved_batch, 'round1': sample['round1'],
                 'game': {level: sample['game'][level] for level in ('elementary', 'advanced')},
                 'intro': {key: sample[key] for key in ('opening', 'closing', 'warmup', 'subtitle', 'tagline')}}

    def interrupted(_, model, *, resume, on_progress):
        assert resume is None and model == 'qwen3:8b'
        on_progress(1, 11, saved_batch)
        raise RuntimeError('Local connection lost')

    def continue_run(_, model, *, resume, on_progress):
        assert resume == saved_batch and model == 'qwen3:8b'
        on_progress(11, 11, completed)
        return sample

    with patch('src.ai_content.available_models', return_value=['qwen3:8b']), \
         patch('src.invitation_content.detect_category', return_value='spontaneous') as classify, \
         patch('src.toolkit.generate_toolkit', return_value=demo_spontaneous_toolkit(topic)), \
         patch('src.spontaneous_content.generate_spontaneous', side_effect=[None]) as generate:
        generate.side_effect = interrupted
        first = AppTest.from_file(str(APP)).run()
        first.text_input(key='topic_input').set_value(topic).run()
        first.button(key='generate').click().run()
        assert first.error and 'Local connection lost' in first.error[0].value
        classify.assert_called_once_with(topic, 'qwen3:8b')
        classify.side_effect = AssertionError('Recover the checkpoint concept before asking Ollama')
        generate.side_effect = continue_run
        reopened = AppTest.from_file(str(APP)).run()
        assert reopened.button(key='generate').label == 'Resume Spontaneous Talk generation'
        reopened.button(key='generate').click().run()
        assert not reopened.error and not reopened.exception
        assert reopened.session_state['brief'] == sample
        assert AppTest.from_file(str(APP)).run().button(key='generate').label == 'Generate Spontaneous Talk session'
        classify.assert_called_once()


def test_changing_topic_updates_the_route_and_allows_retry_after_classification_failure(prepared_local_ai):
    with patch('src.invitation_content.detect_category', side_effect=[
        'spontaneous', RuntimeError('classifier temporarily unavailable'), 'pop_culture',
    ]) as classify:
        app = AppTest.from_file(str(APP)).run()
        app.text_input(key='topic_input').set_value('A funny misunderstanding').run()
        assert 'Spontaneous Talk' in app.button(key='generate').label
        app.text_input(key='topic_input').set_value('Streaming culture').run()
        assert app.button(key='generate').disabled
        assert any('classifier temporarily unavailable' in alert.value for alert in app.warning)
        app.button(key='retry_concept').click().run()
        assert not app.button(key='generate').disabled
        assert any('Pop Culture' in row.value and 'prototype' in row.value for row in app.markdown)
        app.button(key='generate').click().run()
        assert not app.error and not app.exception
        assert app.session_state['metadata']['concept'] == 'pop_culture'
        assert 'workflow' not in app.session_state['metadata']
        assert classify.call_count == 3


def test_local_review_and_regeneration_clear_export():
    from src.ai_content import demo_brief
    brief=demo_brief('Travel')
    updated=demo_brief('Travel')
    updated['subtitle']='New local subtitle'
    report={'summary':'Check the game logic.','issues':[{
        'section':'game_cards','severity':'warning','message':'Make the second consequence more direct.'}]}
    with patch('src.ai_content.available_models',return_value=['qwen3:8b']), \
         patch('src.ai_content.create_with_ollama',return_value=brief) as generate, \
         patch('src.ai_content.review_brief',return_value=report), \
         patch('src.ai_content.regenerate_section',return_value=updated):
        app=AppTest.from_file(str(APP),default_timeout=20).run()
        app.text_input(key='topic_input').set_value('Travel')
        app.selectbox(key='concept_input').set_value('culture_exchange').run()
        app.button(key='generate').click().run()
        assert generate.call_args.kwargs['model']=='qwen3:8b'
        app.button(key='review_content').click().run()
        assert app.session_state['review']==report
        app.session_state['package']=b'old package'
        app.button(key='regenerate').click().run()
        assert app.session_state['brief']['subtitle']=='New local subtitle'
        assert 'package' not in app.session_state and 'review' not in app.session_state
        assert not app.exception


def test_remaining_critical_errors_gate_export_and_override_is_revision_specific():
    from copy import deepcopy
    from src.ai_content import demo_brief
    brief=demo_brief('Travel')
    changed=deepcopy(brief)
    changed['tagline']='A revised travel invitation'
    report={'summary':'Game needs repair','issues':[{
        'section':'game_cards','severity':'error','message':'The consequence is unrelated.'}]}
    repaired={'content':brief,'review':report,'repaired_section':'game_cards'}
    with patch('src.ai_content.available_models',return_value=['qwen3:8b']), \
         patch('src.ai_content.create_with_ollama',return_value=brief), \
         patch('src.ai_content.review_brief',return_value=report), \
         patch('src.ai_content.repair_reviewed_brief',return_value=repaired) as repair, \
         patch('src.ai_content.regenerate_section',return_value=changed):
        app=AppTest.from_file(str(APP),default_timeout=20).run()
        app.text_input(key='topic_input').set_value('Travel')
        app.selectbox(key='concept_input').set_value('culture_exchange').run()
        app.button(key='generate').click().run()
        repair.assert_called_once()
        assert app.button(key='build').disabled
        override=next(item for item in app.checkbox if 'I reviewed' in item.label)
        override.set_value(True).run()
        assert not app.button(key='build').disabled
        app.button(key='regenerate').click().run()
        app.button(key='review_content').click().run()
        assert app.button(key='build').disabled
        assert not app.exception


def test_failed_automatic_repair_preserves_content_and_does_not_pass_review():
    from src.ai_content import demo_brief
    brief=demo_brief('Travel')
    report={'summary':'Needs repair','issues':[{
        'section':'game_cards','severity':'error','message':'Unrelated consequence.'}]}
    with patch('src.ai_content.available_models',return_value=['qwen3:8b']), \
         patch('src.ai_content.create_with_ollama',return_value=brief), \
         patch('src.ai_content.review_brief',return_value=report), \
         patch('src.ai_content.repair_reviewed_brief',side_effect=RuntimeError('server stopped')):
        app=AppTest.from_file(str(APP),default_timeout=20).run()
        app.text_input(key='topic_input').set_value('Travel')
        app.selectbox(key='concept_input').set_value('culture_exchange').run()
        app.button(key='generate').click().run()
        assert app.session_state['brief']==brief and app.session_state['review']==report
        assert 'Automatic repair failed' in app.session_state['review_warning']
        assert app.button(key='build').disabled and not app.exception
