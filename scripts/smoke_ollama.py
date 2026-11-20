"""Opt-in integration check using the actual downloaded local model, never a paid API."""
from argparse import ArgumentParser
from io import BytesIO
import json
from pathlib import Path
import sys
from time import perf_counter
from urllib.request import urlopen
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from pptx import Presentation
from src.ai_content import MODEL, HOST, available_models, create_with_ollama, review_brief, regenerate_section
from src.render_assets import build_gif, build_mini_deck


def main():
    parser=ArgumentParser()
    parser.add_argument('--topic',default='Unexpected Travel Adventures')
    parser.add_argument('--model',default=MODEL)
    args=parser.parse_args()
    if args.model not in available_models():
        raise RuntimeError('Selected local model is not downloaded or Ollama is not running.')
    root=Path(__file__).resolve().parents[1]/'output'/'ollama-smoke'
    root.mkdir(parents=True,exist_ok=True)
    timings={}
    start=perf_counter()
    print(f'Generating prototype locally with {args.model}...',flush=True)
    brief=create_with_ollama(args.topic,args.model)
    timings['generation_seconds']=round(perf_counter()-start,2)
    (root/'generated-content.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'PASS: structured local content ({timings["generation_seconds"]} seconds). Reviewing...',flush=True)
    start=perf_counter()
    review=review_brief(args.topic,brief,args.model)
    timings['review_seconds']=round(perf_counter()-start,2)
    (root/'local-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'PASS: local review ({timings["review_seconds"]} seconds). Regenerating tagline...',flush=True)
    start=perf_counter()
    updated=regenerate_section(args.topic,brief,'tagline','Make it concise and specific to this topic.',args.model)
    assert all(updated[key]==value for key,value in brief.items() if key!='tagline')
    timings['regeneration_seconds']=round(perf_counter()-start,2)
    # The review belongs to the original revision; retain it as a development log,
    # not as an approval of the changed content.
    print('PASS: only selected section replaced. Rendering local PPTX and GIF...',flush=True)
    pptx=build_mini_deck(args.topic,updated)
    gif=build_gif(args.topic,updated)
    assert len(Presentation(BytesIO(pptx)).slides)==5
    with Image.open(BytesIO(gif)) as image:
        assert image.size==(1080,1920) and image.n_frames>1 and image.info['loop']==0
        image.seek(image.n_frames-1)
        image.convert('RGB').resize((324,576)).save(root/'invitation-phone.png')
    with urlopen(f'{HOST}/api/version',timeout=5) as response:
        version=json.load(response)
    report={'topic':args.topic,'event':{'venue':'','date':'','time':''},'model':args.model,
            'ollama':version,'stage':'prototype','timings':timings,'content':updated,
            'review':None,'review_status':'Content changed after initial review; review again before publishing.'}
    as_json=json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8')
    (root/'TalkLine_Prototype.pptx').write_bytes(pptx)
    (root/'TalkLine_Invitation.gif').write_bytes(gif)
    (root/'content.json').write_bytes(as_json)
    with zipfile.ZipFile(root/'TalkLine_Prototype.zip','w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('TalkLine_Prototype.pptx',pptx)
        archive.writestr('TalkLine_Invitation.gif',gif)
        archive.writestr('content.json',as_json)
    print(f'PASS: actual local AI pipeline. Timings: {timings}. Files: {root}',flush=True)


if __name__=='__main__':
    main()
