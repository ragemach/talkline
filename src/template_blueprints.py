"""Inventory native reference shapes without changing the PowerPoint file."""
import hashlib
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


SPONTANEOUS_ROLES = (
    'cover', 'warmup', 'toolkit_a2', 'toolkit_b1', 'toolkit_b2_c1',
    'mini_grammar', 'round1_intro', *('discussion' for _ in range(10)),
    'break', 'round2_intro', 'how_to_play', 'play', 'cooldown', 'feedback',
)


def content_bindings(number):
    """Explicit content destinations; all other reference text stays fixed.

    Toolkit pagination and mechanic-specific game fields need separate rendering
    policies before they can be bound safely.
    """
    if number == 1:
        return {(7,): 'topic', (8,): 'deck.subtitle'}
    if number == 2:
        return {(shape,): f'deck.warmup.{index}'
                for index, shape in enumerate((10, 14, 18))}
    if 8 <= number <= 17:
        return {(shape,): f'deck.round1.{number - 8}.{field}'
                for shape, field in ((7, 'title'), (15, 'a2'), (21, 'b2'), (27, 'c1'))}
    if number == 22:
        return {(group, shape): f'deck.cooldown.{index}'
                for index, (group, shape) in enumerate(((14, 16), (22, 24), (30, 32)))}
    return {}


def text_shapes(shapes, parent=()):
    """Yield ID paths, including text within groups; IDs are local to a group."""
    for shape in shapes:
        path = (*parent, shape.shape_id)
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from text_shapes(shape.shapes, path)
        elif shape.has_text_frame and shape.text.strip():
            yield path, shape


def inspect_spontaneous_template(path: Path) -> dict:
    """Capture sample geometry and styles as renderer inputs, not approval."""
    path = Path(path)
    source = path.read_bytes()
    presentation = Presentation(path)
    if len(presentation.slides) != len(SPONTANEOUS_ROLES):
        raise ValueError('Expected the approved 23-slide Spontaneous Talk sample')
    slides = []
    for number, (slide, role) in enumerate(zip(presentation.slides,
                                               SPONTANEOUS_ROLES), 1):
        fields = []
        bindings = content_bindings(number)
        for shape_path, shape in text_shapes(slide.shapes):
            fields.append({
                'shape_path': list(shape_path), 'name': shape.name,
                'sample_text': shape.text,
                'content_key': bindings.get(shape_path),
                # Nested coordinates are local to the containing group.
                'bounds_emu': [shape.left, shape.top, shape.width, shape.height],
                'paragraphs': [
                    {'runs': [{'text': run.text, 'font': run.font.name,
                               'size_pt': run.font.size.pt if run.font.size else None,
                               'bold': run.font.bold, 'italic': run.font.italic}
                              for run in paragraph.runs]}
                    for paragraph in shape.text_frame.paragraphs],
            })
        missing = set(bindings) - {tuple(field['shape_path']) for field in fields}
        if missing:
            raise ValueError(f'Slide {number}: required template fields are missing: {missing}')
        slides.append({'source_slide': number, 'role': role, 'fields': fields,
                       'sample_notes': slide.notes_slide.notes_text_frame.text
                       if slide.has_notes_slide else ''})
    return {'blueprint_version': 1, 'concept': 'spontaneous',
            'source_file': path.name, 'source_sha256': hashlib.sha256(source).hexdigest(),
            'size_emu': [presentation.slide_width, presentation.slide_height],
            'slides': slides}


def verify_blueprint_source(blueprint: dict, path: Path) -> None:
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != blueprint['source_sha256']:
        raise ValueError('Reference template changed; rebuild its blueprint before exporting')
