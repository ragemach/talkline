"""Run the real offline prototype, save reviewable artifacts, and check them."""
from io import BytesIO
from pathlib import Path
import json
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from pptx import Presentation
from src.ai_content import demo_brief
from src.render_assets import build_gif, build_mini_deck


def main():
    target = Path(__file__).resolve().parents[1] / 'output' / 'smoke-demo'
    target.mkdir(parents=True, exist_ok=True)
    topic = 'Unexpected Travel Adventures'
    brief = demo_brief(topic)
    pptx = build_mini_deck(topic, brief)
    gif = build_gif(topic, brief, venue='', date_label='', time_label='')
    (target / 'TalkLine_Prototype.pptx').write_bytes(pptx)
    (target / 'TalkLine_Invitation.gif').write_bytes(gif)
    (target / 'content.json').write_text(json.dumps(brief, indent=2), encoding='utf-8')
    with zipfile.ZipFile(target / 'TalkLine_Prototype.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in ('TalkLine_Prototype.pptx', 'TalkLine_Invitation.gif', 'content.json'):
            archive.write(target / name, name)
    assert len(Presentation(BytesIO(pptx)).slides) == 5
    with Image.open(BytesIO(gif)) as im:
        assert im.format == 'GIF' and im.size == (1080, 1920)
        assert im.info['loop'] == 0 and im.n_frames > 1
        duration = 0
        for i in range(im.n_frames):
            im.seek(i)
            duration += im.info['duration']
        assert duration == 6000
        im.seek(im.n_frames - 1)
        im.convert('RGB').save(target / 'invitation-final.png')
        im.convert('RGB').resize((324, 576)).save(target / 'invitation-phone.png')
    print(f'PASS: 5 editable slides, animated 1080x1920 GIF, {duration}ms, ZIP. Files: {target}')


if __name__ == '__main__':
    main()
