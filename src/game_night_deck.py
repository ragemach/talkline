"""Build an editable Game Night using the approved two-game PowerPoint."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import re

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from src.game_night_export import RULES
from src.session_sequence import RATE_US_URL
from src.spontaneous_deck import (
    _arrange_slides, _fit_top_level, _line_count, _notes, _remove, _shape, _write,
)
from src.template_blueprints import verify_blueprint_source
from src.toolkit import LEVEL_LABELS, validate_level


REFERENCE = (
    Path(__file__).resolve().parents[1] / 'references' / 'user_examples'
    / 'TALKLINE GAMENIGHT TABOO-PROBLEM SOLVER.pptx'
)
BLUEPRINT = {
    'source_file': REFERENCE.name,
    'source_sha256': 'ff578aa9f34c50c4de727caba40f590899aaed7429a5a589bd480b7955243681',
}
MECHANICS = ('taboo', 'problem_solver')
COLUMNS = ((.46, 3.24), (3.8, 3.24))
FULL_COLUMN = (.46, 6.58)
TOOLKIT_TOP = 1.91
GRAMMAR_TOP = 1.82
PAGE_BOTTOM = 9.26
CARD_GAP = .08
GRAMMAR_GAP = .13

TABOO_STEPS = (
    ('Choose a level', 'Choose Elementary (A2–B1) or Advanced (B2–C1).'),
    ('Start the timer', 'Only the clue giver should see the target and forbidden clues.'),
    ('Describe the word', 'Avoid the target and every forbidden clue.'),
    ('Record the result', 'Use Correct for a guess, Forbidden word for a loss, or Skip.'),
    ('Switch teams', 'Switch after the timer ends, or use End turn.'),
    ('Check the scores', 'Each correct guess earns one point. The highest score wins.'),
)
PROBLEM_SOLVER_STEPS = (
    ('Read the problem', 'The active team gets a new challenge.'),
    ('Discuss solutions', 'Consider options and agree on one solution.'),
    ('Present the solution', 'Explain what you would do and why it would work.'),
    ('Award up to three points', 'The other team gives one, two, or three points.'),
    ('Switch roles', 'The other team gets the next problem.'),
    ('Keep playing', 'Play the remaining cards and compare the final scores.'),
)


def _text(value):
    return ' '.join(value.split())


def _template(slide, path, text, max_bottom, *, size=None, lead=None):
    shape = _write(slide, path, _text(text))
    if size is not None:
        shape.text_frame.paragraphs[0].runs[0].font.size = Pt(size)
    _fit_top_level(shape, Inches(max_bottom), size=size, lead=lead)
    return shape


def _button(slide, button_path, background_path, address):
    button = _shape(slide, button_path)
    for paragraph in button.text_frame.paragraphs:
        for run in paragraph.runs:
            if run.hyperlink.address:
                run.hyperlink.address = None
    button.click_action.hyperlink.address = address
    _shape(slide, background_path).click_action.hyperlink.address = address


def _clone_toolkit(presentation, source):
    """Copy a Toolkit layout, including the original linked background artwork."""
    slide = presentation.slides.add_slide(source.slide_layout)
    element = deepcopy(source._element)
    relationships = {}
    for rel in source.part.rels.values():
        kind = rel.reltype.rsplit('/', 1)[-1]
        if kind == 'image' and not rel.is_external:
            relationships[rel.rId] = slide.part.relate_to(rel.target_part, rel.reltype)
        elif kind != 'slideLayout':
            raise ValueError('Game Night Toolkit contains an unmapped relationship.')
    for node in element.iter():
        for attr in ('r:embed', 'r:link', 'r:id'):
            name = qn(attr)
            if node.get(name) in relationships:
                node.set(name, relationships[node.get(name)])
    slide._element = slide.part._element = element
    slide.__dict__.pop('shapes', None)
    return slide


def _only(slide, *ids):
    keep = set(ids)
    _remove(slide, *(shape.shape_id for shape in slide.shapes if shape.shape_id not in keep))


def _round_panel(slide, x, y, width, height, color):
    panel = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(width), Inches(height)
    )
    panel.adjustments[0] = .06
    panel.fill.solid()
    panel.fill.fore_color.rgb = RGBColor.from_string(color)
    panel.line.fill.background()
    return panel


def _style_specs(item):
    kind, data = item
    if kind == 'grammar':
        label, entry = data
        return (
            (f'{label} / {entry["title"]}', 16, True, 'FFFFFF'),
            (entry['pattern'], 13, True, 'FFE39B'),
            (entry['explanation'], 13, False, 'EBF1F9'),
            *((example, 13, False, 'DBE7F5') for example in entry['examples']),
        )
    return (
        (('Idiom: ' if kind == 'idioms' else '') + data['expression'], 14, True, 'FFFFFF'),
        (data['turkish'], 12.5, False, 'FFE39B'),
        (data['example'], 12.5, False, 'D9E6F5'),
    )


def _card_height(item, width):
    points = sum(_line_count(_text(value), (width - .28) * 72, size, bold=bold) * (size + 2)
                 for value, size, bold, _ in _style_specs(item))
    return (points + 11) / 72


def _card(slide, x, y, width, item):
    height = _card_height(item, width)
    panel = _round_panel(slide, x, y, width, height, '2C5079')
    panel.name = 'Toolkit grammar panel' if item[0] == 'grammar' else 'Toolkit entry panel'
    text = slide.shapes.add_textbox(
        Inches(x + .14), Inches(y + .06), Inches(width - .28), Inches(height - .09)
    )
    text.name = 'Toolkit grammar' if item[0] == 'grammar' else 'Toolkit entry'
    frame = text.text_frame
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    for index, (value, size, bold, color) in enumerate(_style_specs(item)):
        paragraph = frame.add_paragraph() if index else frame.paragraphs[0]
        paragraph.line_spacing = Pt(size + 2)
        paragraph.space_after = paragraph.space_before = Pt(0)
        run = paragraph.add_run()
        run.text = _text(value)
        run.font.name = 'Arial'
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = RGBColor.from_string(color)
    return height


def _maximum_cards(items, width, room, gap=CARD_GAP):
    for index, item in enumerate(items):
        room -= _card_height(item, width) + gap
        if room < 0:
            return index
    return len(items)


def _layout_toolkit(items):
    """Fit pages greedily, balancing both columns on the last page."""
    pages = []
    room = PAGE_BOTTOM - TOOLKIT_TOP - .28
    while items:
        wide = _maximum_cards(items, FULL_COLUMN[1] - .26, room)
        if wide == len(items):
            pages.append((items,))
            break
        width = COLUMNS[0][1] - .26
        left = _maximum_cards(items, width, room)
        right = _maximum_cards(items[left:], width, room)
        if wide >= left + right:
            if not wide:
                raise ValueError('A Toolkit entry is too long for a Game Night page.')
            pages.append((items[:wide],))
            items = items[wide:]
        elif left + right == len(items):
            minimum = left
            while minimum > 1 and _maximum_cards(items[minimum - 1:], width, room) == len(items) - minimum + 1:
                minimum -= 1
            height = lambda entries: sum(_card_height(item, width) + CARD_GAP for item in entries)
            split = min(range(minimum, left + 1), key=lambda n: abs(height(items[:n]) - height(items[n:])))
            pages.append((items[:split], items[split:]))
            break
        else:
            pages.append((items[:left], items[left:left + right]))
            items = items[left + right:]
    return pages


def _level_pages(presentation, source, label, level):
    items = [(kind, item) for kind in ('vocabulary', 'phrases', 'idioms') for item in level[kind]]
    layout = _layout_toolkit(items)
    pages = [source, *[_clone_toolkit(presentation, source) for _ in layout[1:]]]
    for number, (slide, columns) in enumerate(zip(pages, layout, strict=True), 1):
        _only(slide, 2, 5, 6, 69)
        title = _shape(slide, (5,))
        title.width = Inches(6.4)
        _template(slide, (5,), f'Game Night Toolkit / {label}', 1.32)
        _template(slide, (6,), 'Vocabulary, phrases and idioms for both games.', 1.86, size=12)
        footer = _shape(slide, (69,))
        footer.left, footer.width = Inches(.55), Inches(6.4)
        _write(slide, (69,), f'Toolkit / {label} / {number} of {len(layout)}')
        bounds = (FULL_COLUMN,) if len(columns) == 1 else COLUMNS
        for (x, width), entries in zip(bounds, columns, strict=True):
            card_width = width - .26
            total = .28 + sum(_card_height(item, card_width) + CARD_GAP for item in entries)
            _round_panel(slide, x, TOOLKIT_TOP, width, total, '233F68')
            y = TOOLKIT_TOP + .14
            for item in entries:
                y += _card(slide, x + .13, y, card_width, item) + CARD_GAP
        _notes(slide, f'{label} Toolkit. Ask learners to try one expression in each game.')
    return pages


def _grammar_pages(presentation, source, toolkit):
    rows = [('grammar', (label, toolkit['levels'][level]['mini_grammar']))
            for level, label in LEVEL_LABELS.items()]
    room = PAGE_BOTTOM - GRAMMAR_TOP
    layout = []
    while rows:
        count = _maximum_cards(rows, FULL_COLUMN[1], room, GRAMMAR_GAP)
        if not count:
            raise ValueError('A mini grammar is too long for a Game Night page.')
        layout.append(rows[:count])
        rows = rows[count:]
    pages = [source, *[_clone_toolkit(presentation, source) for _ in layout[1:]]]
    for number, (slide, rows) in enumerate(zip(pages, layout, strict=True), 1):
        _only(slide, 2, 5, 8)
        _write(slide, (2, 4), 'MINI GRAMMAR')
        _write(slide, (5,), 'Game Night Toolkit / Mini Grammar')
        footer = _shape(slide, (8,))
        footer.left, footer.width = Inches(.55), Inches(6.4)
        _write(slide, (8,), f'Mini Grammar / {number} of {len(layout)}')
        x, width = FULL_COLUMN
        y = GRAMMAR_TOP
        for item in rows:
            y += _card(slide, x, y, width, item) + GRAMMAR_GAP
        _notes(slide, 'Model the pattern and example. Invite learners to make a new example in their group.')
    return pages


def _rules_slide(slide, steps, fields, button, backing, filename, mechanic):
    for (title, body), (heading, detail) in zip(steps, fields, strict=True):
        title_box = _shape(slide, (heading,))
        title_box.width = Inches(5.1)
        _template(slide, (heading,), title, title_box.top.inches + .26, size=12, lead=13)
        body_box = _shape(slide, (detail,))
        _template(slide, (detail,), body, body_box.top.inches + .4, size=11, lead=12)
    _button(slide, button, backing, filename)
    _notes(slide, '\n'.join((*RULES[mechanic],
                             f'Click the game button or open {filename} from the same folder.')))


def build_game_night_deck(topic, content, toolkit, game_files, *, feedback_url=RATE_US_URL):
    """Produce the approved Game Night sequence with two independent local links."""
    if len(game_files) != 2 or len({file.casefold() for file in game_files}) != 2 or not all(
        re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.html', file, flags=re.ASCII) for file in game_files
    ):
        raise ValueError('Game Night needs two distinct HTML filenames in the same folder as the deck.')
    if len(content['warmup']) != 3 or tuple(game['mechanic'] for game in content['games']) != MECHANICS:
        raise ValueError('Game Night needs three warm-ups, then Taboo and Problem Solver.')
    if toolkit['topic'].strip().casefold() != topic.strip().casefold():
        raise ValueError('The Toolkit belongs to a different session topic.')
    for level in LEVEL_LABELS:
        validate_level(toolkit['levels'][level], level)

    verify_blueprint_source(BLUEPRINT, REFERENCE)
    presentation = Presentation(REFERENCE)
    slides = list(presentation.slides)
    presentation.core_properties.title = topic
    presentation.core_properties.subject = 'TalkLine Game Night'
    taboo, problem = content['games']

    cover, warmup = slides[:2]
    _template(cover, (13,), topic, 2.07, lead=20)
    _template(cover, (17,), content['subtitle'], 8.83, size=12)
    _notes(cover, f'{content["tagline"]}\nTonight’s topic is {topic}. First play Taboo, then Problem Solver.')
    _template(warmup, (6,), content['opening'], 2.22, size=13, lead=15)
    for shape_id, question in zip((10, 19, 17), content['warmup'], strict=True):
        shape = _shape(warmup, (shape_id,))
        _template(warmup, (shape_id,), question, shape.top.inches + .64, lead=18)
    _notes(warmup, f'{content["opening"]}\nInvite one short answer per person.')

    toolkit_slides = []
    for index, (level, label) in enumerate(LEVEL_LABELS.items(), 2):
        toolkit_slides.extend(_level_pages(presentation, slides[index], label, toolkit['levels'][level]))
    grammar_slides = _grammar_pages(presentation, slides[5], toolkit)

    _write(slides[6], (7,), 'One target, with forbidden clues. Can your team guess it?')
    _remove(slides[6], 24, 28)
    for background_id, label_id, center, label in (
        (20, 22, 2.26, 'ELEMENTARY / A2–B1'),
        (26, 29, 5.24, 'ADVANCED / B2–C1'),
    ):
        badge = _shape(slides[6], (background_id,))
        badge.left, badge.width = Inches(center - 1), Inches(2)
        text = _write(slides[6], (label_id,), label)
        text.left, text.width = badge.left, badge.width
    _notes(slides[6], f'{taboo["title"]}\nPick teams and place the screen where only the clue giver can see it.')
    _rules_slide(slides[7], TABOO_STEPS,
                 [(13 + 9 * i, 14 + 9 * i) for i in range(6)], (62,), (60, 61),
                 game_files[0], 'taboo')
    _notes(slides[8], 'Take a 20-minute break. Tell everyone what time to come back for Problem Solver.')
    _notes(slides[9], f'{problem["title"]}\nKeep the same teams or give everyone a new partner.')
    _rules_slide(slides[10], PROBLEM_SOLVER_STEPS,
                 [(52 + 2 * i, 53 + 2 * i) for i in range(6)], (64,), (49, 50),
                 game_files[1], 'problem_solver')

    cooldown = slides[11]
    _template(cooldown, (6,), content['closing'], 2.24, size=13, lead=15)
    for shape_id, prompt in zip((10, 14, 18), (
        'Which clue helped your team guess a word?',
        'Which solution would you try?',
        'What is one English expression you used tonight?',
    ), strict=True):
        _write(cooldown, (shape_id,), prompt)
    _notes(cooldown, content['closing'])
    _button(slides[12], (10,), (5, 6), feedback_url)
    _notes(slides[12], 'Thank the group and invite feedback. The Rate Us form needs internet.')

    _arrange_slides(presentation, [*slides[:2], *toolkit_slides, *grammar_slides, *slides[6:]])
    result = BytesIO()
    presentation.save(result)
    return result.getvalue()
