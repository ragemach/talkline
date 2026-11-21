from html import escape
from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from src.run_state import LOCAL_MODE
from src.run_store import SavedRun
from src.session_sequence import FULL_SPONTANEOUS
from src.settings import UserSettings
from src.spontaneous_content import generate_spontaneous
from src.spontaneous_demo_toolkit import demo_spontaneous_toolkit


def test_saved_preview_keeps_each_tier_and_shows_the_current_form_concept(monkeypatch):
    topic = 'Everyday choices'
    brief = generate_spontaneous(topic)
    shared = 'The library opens at 8 a.m.'
    questions = ('Where would you read?', 'Why do groups arrive early?', 'Should hours change even if staffing costs rise?')
    brief['round1'][1].update({level: f'{shared} {q}' for level, q in zip(('a2', 'b2', 'c1'), questions)})
    brief['round1'][2].update(a2='What would you bring?', b2='What do other people bring?',
                              c1='Who should cover the cost of shared supplies?')
    toolkit = demo_spontaneous_toolkit(topic)
    toolkit['levels']['a2']['mini_grammar']['pattern'] = '<subject> + verb'
    saved = SavedRun({
        'metadata': {'topic': topic, 'concept': 'spontaneous', 'workflow': FULL_SPONTANEOUS,
                     'date': '', 'time': '', 'venue': 'A & B', 'mode': LOCAL_MODE, 'model': 'qwen3:8b'},
        'brief': brief, 'toolkit': toolkit,
    })
    list_models = Mock(return_value=['qwen3:8b'])
    monkeypatch.setattr('src.run_store.load_run', lambda: saved)
    monkeypatch.setattr('src.settings.load_settings', UserSettings)
    monkeypatch.setattr('src.ai_content.available_models', list_models)
    monkeypatch.setattr('src.checkpoints.load_session_progress', lambda *_: None)
    monkeypatch.setattr('src.checkpoints.load_automatic_concept', lambda *_: None)
    monkeypatch.setattr('src.invitation_content.detect_category', lambda *_: 'business')

    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    assert not app.error and not app.exception
    list_models.assert_called_once_with()
    markup = [item.value for item in app.markdown]
    cards = [html for html in markup if '<div class="tl-round-card">' in html]
    assert len(cards) == 10
    assert 'class="tl-card-scene"' not in cards[0]
    assert all(escape(brief['round1'][0][level]) in cards[0] for level in ('a2', 'b2', 'c1'))
    assert cards[1].count(shared) == 1
    assert all(question in cards[1] for question in questions)
    assert 'class="tl-card-scene"' not in cards[2]
    assert cards[2].count('What would you bring?') == 1
    assert any('&lt;subject&gt; + verb' in item for item in markup)
    event = next(html for html in markup if '<div class="tl-meta-grid">' in html)
    assert 'A &amp; B' in event and event.count('Not specified') == 2

    app.text_input(key='topic_input').set_value('Salary negotiations').run()
    assert not app.error and not app.exception
    status = next(item.value for item in app.markdown if '<div class="tl-status-bar">' in item.value)
    assert 'Business English' in status and 'Business English' in app.button(key='generate').label
    assert list_models.call_count == 2
