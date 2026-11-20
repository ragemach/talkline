from io import BytesIO
import pytest
from PIL import Image
from pptx import Presentation
from src.ai_content import demo_brief
from src.render_assets import build_gif, build_mini_deck, _wrap, _choose_font


def test_editable_mini_deck_and_notes():
    prs = Presentation(BytesIO(build_mini_deck('Unexpected Travel Adventures', demo_brief('Travel'))))
    assert len(prs.slides) == 5
    texts = []
    for slide in prs.slides:
        assert slide.notes_slide.notes_text_frame.text.strip()
        for shape in slide.shapes:
            assert shape.left >= 0 and shape.top >= 0
            assert shape.left + shape.width <= prs.slide_width
            assert shape.top + shape.height <= prs.slide_height
            if shape.has_text_frame:
                texts.append(shape.text)
    assert 'UNEXPECTED TRAVEL ADVENTURES' in texts
    assert any('A2' == text for text in texts)


def test_full_hd_animated_gif():
    data = build_gif('Unexpected Travel Adventures', demo_brief('Travel'))
    with Image.open(BytesIO(data)) as gif:
        assert gif.format == 'GIF' and gif.size == (1080, 1920)
        assert gif.info['loop'] == 0 and gif.n_frames > 1
        duration = 0
        gif.seek(0)
        first = gif.convert('RGB').tobytes()
        for i in range(gif.n_frames):
            gif.seek(i)
            duration += gif.info['duration']
        assert duration == 6000
        assert gif.convert('RGB').tobytes() != first
    assert len(data) < 30 * 1024 * 1024


@pytest.mark.parametrize('options', [{'fps': 0}, {'fps': 31}, {'fps': 1.5}, {'seconds': 3}, {'seconds': 6.5}])
def test_bad_animation_parameters(options):
    with pytest.raises(ValueError):
        build_gif('Travel', demo_brief('Travel'), **options)


def test_long_unbroken_title_wraps_to_width():
    from PIL import ImageDraw
    draw = ImageDraw.Draw(Image.new('RGB', (1080, 1920)))
    font = _choose_font(True, 78)
    lines = _wrap('W' * 110, font, 960, draw)
    assert all(draw.textlength(line, font=font) <= 960 for line in lines)
