from io import BytesIO
from zipfile import ZipFile

from pptx import Presentation
import pytest

from src.session_sequence import RATE_US_URL
from src.spontaneous_deck import build_spontaneous_deck
from src.template_blueprints import text_shapes
from src.toolkit_library import sample_toolkit


def _session():
    return {
        'subtitle': 'Easy ways to start a conversation',
        'tagline': 'Get to know a new person tonight.',
        'opening': 'Think of someone you enjoy spending time with. What made it easy to get to know them?',
        'closing': 'Thank you for talking with us. Which idea from the game would help a new person join in?',
        'warmup': ['How was your day?', 'Do you like meeting new people?', 'How was your week?'],
        'round1': [
            {'title': f'Friendly conversation {number}', 'a2': f'What do you ask at table {number}?',
             'b2': f'How would you invite a shy guest at table {number} to join in?',
             'c1': f'How can you include someone at table {number} without putting them on the spot?'}
            for number in range(1, 11)
        ],
        'game': {'elementary': [None] * 20, 'advanced': [None] * 20},
    }


def _text(slide):
    return '\n'.join(shape.text for _, shape in text_shapes(slide.shapes))


def test_reference_deck_has_ten_editable_cards_notes_and_real_links():
    content = _session()
    output = build_spontaneous_deck('Meeting new people', content)
    presentation = Presentation(BytesIO(output))
    assert (presentation.slide_width, presentation.slide_height) == (6858000, 9144000)
    assert len(presentation.slides) == 19
    slides = list(presentation.slides)
    assert 'Meeting new people' in _text(slides[0])
    assert 'WHAT IF...?' not in _text(slides[0])
    assert content['opening'] in _text(slides[1])
    assert all(question in _text(slides[1]) for question in content['warmup'])
    assert all(slide.notes_slide.notes_text_frame.text for slide in slides)
    for card, slide in zip(content['round1'], slides[3:13], strict=True):
        assert all(value in _text(slide) for value in card.values())
        assert {label for label in ('A2', 'B2', 'C1') if label in _text(slide).splitlines()} == {
            'A2', 'B2', 'C1'}
    assert content['closing'] in _text(slides[-2])
    links = [{rel.target_ref for rel in slide.part.rels.values() if rel.is_external}
             for slide in slides]
    assert links[-3] == {'TalkLine_Game.html'}
    assert links[-1] == {RATE_US_URL}
    with ZipFile(BytesIO(output)) as archive:
        assert archive.testzip() is None
        assert all(b'netlify' not in archive.read(name) for name in archive.namelist()
                   if name.endswith(('.rels', '.xml')))


def test_toolkit_pages_keep_learners_and_grammar_separate():
    toolkit = sample_toolkit()
    presentation = Presentation(BytesIO(build_spontaneous_deck(toolkit['topic'], _session(), toolkit)))
    pages = [_text(slide) for slide in presentation.slides]
    first_round = next(index for index, text in enumerate(pages) if 'Discussion Questions' in text)
    toolkit_pages = pages[2:first_round]
    assert len(toolkit_pages) > 4
    for key, label in [('a2', 'A1/A2'), ('b1', 'B1'), ('b2_c1', 'B2/C1')]:
        vocab = '\n'.join(text for text in toolkit_pages if f'{label} / Vocabulary' in text)
        grammar = '\n'.join(text for text in toolkit_pages if f'{label} / Grammar' in text)
        material = toolkit['levels'][key]
        for group in ('vocabulary', 'phrases', 'idioms'):
            assert all(value in vocab for item in material[group] for value in item.values())
        assert material['mini_grammar']['pattern'] in grammar
        assert all(example in grammar for example in material['mini_grammar']['examples'])


def test_reject_incomplete_cards_and_unsafe_game_link():
    session = _session()
    with pytest.raises(ValueError, match='same folder'):
        build_spontaneous_deck('Travel', session, game_file='https://example.com/game.html')
    session['round1'].pop()
    with pytest.raises(ValueError, match='ten Round 1'):
        build_spontaneous_deck('Travel', session)
