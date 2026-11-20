"""Developer QA: build five repeatable examples through the actual application engine."""
from pathlib import Path
import sys
import json
from io import BytesIO
import argparse
import time
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from src.ai_content import create_with_ollama,demo_brief,MODEL
from src.invitation_content import prepare_invitation,LABELS
from src.invitation_export import render_invitation,animate_invitation
from src.settings import EventDetails

EXAMPLES={'spontaneous':'Tiny Decisions','business':'Office Boundaries',
          'pop_culture':'One More Episode','culture_exchange':'Small Daily Rituals',
          'game_night':'Odd Objects'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ai',action='store_true')
    parser.add_argument('--model',default=MODEL)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--reuse-brief',action='store_true')
    parser.add_argument('--only',choices=list(EXAMPLES))
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]/'output'/'invitation-examples'
    root.mkdir(parents=True,exist_ok=True)
    event=EventDetails(venue='Holstory Cafe Beşiktaş',time='20:00')
    summary=[]
    for category,topic in EXAMPLES.items():
        if args.only and category!=args.only: continue
        directory=root/category
        directory.mkdir(exist_ok=True)
        if args.resume and all((directory/name).exists() for name in ('content.json','Invitation.gif','Invitation.pptx','Invitation.png','Preview.png')):
            saved=json.loads((directory/'content.json').read_text(encoding='utf-8'))
            summary.append({k:saved[k] for k in ('topic','category','event','seconds')})
            print(f'{category}: reusing completed example',flush=True)
            continue
        start=time.perf_counter()
        print(f'{category}: generating speaking brief for {topic}...',flush=True)
        brief_path=directory/'generated-brief.json'
        if (args.resume or args.reuse_brief) and brief_path.exists(): brief=json.loads(brief_path.read_text(encoding='utf-8'))
        elif args.reuse_brief and (directory/'content.json').exists():
            brief=json.loads((directory/'content.json').read_text(encoding='utf-8'))['content']
        else:
            brief=create_with_ollama(topic,args.model) if args.ai else demo_brief(topic)
            brief_path.write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'{category}: writing fuller invitation copy...',flush=True)
        result=prepare_invitation(topic,brief,event,category,args.model if args.ai else None)
        pptx=result.pop('pptx')
        image=render_invitation(pptx)
        gif=animate_invitation(image)
        with Image.open(BytesIO(gif)) as check:
            assert check.size==image.size and check.n_frames>1 and check.info['loop']==0
        (directory/'Invitation.pptx').write_bytes(pptx)
        (directory/'Invitation.gif').write_bytes(gif)
        image.save(directory/'Invitation.png')
        preview=image.copy();preview.thumbnail((900,900));preview.save(directory/'Preview.png')
        metadata={'topic':topic,'category':LABELS[category],'example':True,'stage':'prototype',
                  'event':{'venue':event.venue,'time':event.time,'date':event.date},
                  'content':brief,'invitation':result,'seconds':round(time.perf_counter()-start,2)}
        (directory/'content.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        summary.append({k:metadata[k] for k in ('topic','category','event','seconds')})
        print(f'{category}: PASS ({metadata["seconds"]} seconds)',flush=True)
    summary=[]
    for category in EXAMPLES:
        metadata=json.loads((root/category/'content.json').read_text(encoding='utf-8'))
        summary.append({k:metadata[k] for k in ('topic','category','event','seconds')})
    (root/'index.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with zipfile.ZipFile(root/'TalkLine_Invitation_Examples.zip','w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(root/'index.json','index.json')
        for category in EXAMPLES:
            for path in (root/category).iterdir(): archive.write(path,f'{category}/{path.name}')
    # Update the already-shared preview paths to the newly generated fuller example.
    old=root.parent/'invitation-engine'
    for suffix,filename in [('gif','Invitation.gif'),('png','Invitation.png'),('pptx','Invitation.pptx')]:
        (old/f'local-ai.{suffix}').write_bytes((root/'spontaneous'/filename).read_bytes())
    (old/'local-ai-preview.png').write_bytes((root/'spontaneous'/'Preview.png').read_bytes())
    (old/'local-ai-copy.json').write_bytes((root/'spontaneous'/'content.json').read_bytes())
    for category in EXAMPLES:
        (old/f'{category}-preview.png').write_bytes((root/category/'Preview.png').read_bytes())
    print(f'PASS: five example kits and combined ZIP: {root}',flush=True)


if __name__=='__main__': main()
