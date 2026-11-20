"""Editable PPTX mini deck and high-resolution portrait GIF creator."""
from __future__ import annotations
import os
import subprocess
import tempfile
import math
from pathlib import Path
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import imageio_ffmpeg

NAVY=(10,12,30); CYAN=(41,216,239); PURPLE=(162,113,243)
WHITE=(246,249,255); PALE=(184,199,220)

def _rect(slide,x,y,w,h,fill,line=None):
    sh=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb=RGBColor(*fill)
    sh.line.fill.background() if line is None else None
    if line is not None: sh.line.color.rgb=RGBColor(*line)
    return sh

def _textbox(slide,text,x,y,w,h,size=20,color=WHITE,bold=False,align=PP_ALIGN.LEFT):
    shape=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=shape.text_frame;tf.word_wrap=True
    tf.margin_left=Inches(.08); tf.margin_right=Inches(.08)
    tf.margin_top=Inches(.04); tf.margin_bottom=Inches(.04)
    p=tf.paragraphs[0];p.alignment=align
    run=p.add_run();run.text=text;run.font.size=Pt(size);run.font.bold=bold
    run.font.color.rgb=RGBColor(*color)
    return shape

def _slide(prs,section):
    slide=prs.slides.add_slide(prs.slide_layouts[6])
    bg=slide.background.fill; bg.solid(); bg.fore_color.rgb=RGBColor(*NAVY)
    _rect(slide,.38,.35,12.55,.68,(25,30,63))
    _textbox(slide,'TALKLINE  ·  '+section.upper(),.62,.49,12,.42,size=14,color=CYAN,bold=True)
    return slide

def build_mini_deck(topic:str,brief:dict,*,game_file:str|None=None)->bytes:
    """A 5-slide functional pipeline demo. The final full TalkLine deck is a future milestone."""
    prs=Presentation()
    prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    s=_slide(prs,'Spontaneous talk')
    _textbox(s,topic.upper(),.8,1.65,11.7,2.1,42,WHITE,True)
    _textbox(s,brief['subtitle'],.85,4.2,11.3,.9,25,CYAN)
    _textbox(s,brief['tagline'],.85,5.35,11.3,.7,18,PALE)

    s=_slide(prs,'Warm-up')
    _textbox(s,'WARM-UP',.75,1.35,10,.6,31,WHITE,True)
    for i,q in enumerate(brief['warmup']):
        y=2.16+i*1.36
        _rect(s,.68,y,11.95,1.1,(29,34,67))
        _textbox(s,f'{i+1:02d}  {q}',.98,y+.18,11.28,.78,20,WHITE)

    for n,item in enumerate(brief['round1'][:2],1):
        s=_slide(prs,f'Round 1 sample · {n}/2')
        _textbox(s,item['title'],.78,1.15,11.9,.64,30,WHITE,True)
        for label,text,color,i in [('A2',item['a2'],CYAN,0),('B2',item['b2'],(187,151,255),1),('C1',item['c1'],(245,194,104),2)]:
            y=2.0+i*1.46
            _rect(s,.7,y,11.92,1.26,(27,31,65))
            _textbox(s,label,.92,y+.33,1.05,.58,18,color,True)
            _textbox(s,text,2.05,y+.19,10.0,.99,20,WHITE)

    s=_slide(prs,'Round 2 · Game')
    _textbox(s,'PATCH NOTES: REALITY UPDATE',.8,1.34,11.8,1.0,32,WHITE,True)
    _textbox(s,'GLITCH   →   PATCH A / B   →   CONSEQUENCE   →   KEEP / RESET',.85,2.58,11.8,1.2,22,CYAN,True)
    if game_file:
        link = _textbox(s,'Open the offline speaking game',.85,4.1,11.6,.6,22,CYAN,True)
        link.text_frame.paragraphs[0].runs[0].hyperlink.address = game_file
        _textbox(s,'Extract the ZIP first. You can also open the game HTML file in your browser.',
                 .85,4.85,11.6,1.0,18,PALE)
    else:
        _textbox(s,'Discuss both patches and choose one before revealing its outcome.',
                 .85,4.5,11.6,1.0,18,PALE)
    for slide in prs.slides:
        slide.notes_slide.notes_text_frame.text = (
            'Prototype sample only. Invite learners to speak in pairs; choose the A2, B2 or C1 '
            'prompt that suits them. Demo content is reusable example material, not topic-specific AI output.'
        )
    buffer=BytesIO();prs.save(buffer)
    return buffer.getvalue()

def _choose_font(bold:bool,size:int):
    paths=[]
    if os.name=='nt':
        paths=[r'C:\Windows\Fonts\segoeuib.ttf' if bold else r'C:\Windows\Fonts\segoeui.ttf',
               r'C:\Windows\Fonts\arialbd.ttf' if bold else r'C:\Windows\Fonts\arial.ttf']
    else:
        paths=['/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
    for path in paths:
        try: return ImageFont.truetype(path,size)
        except (OSError,ValueError): pass
    return ImageFont.load_default(size=size)

def _wrap(text:str, font, max_width:int,draw)->list[str]:
    # Split unusually long tokens too, rather than drawing outside the invitation.
    words=[]
    for word in text.split():
        chunk=''
        for char in word:
            if chunk and draw.textlength(chunk+char,font=font)>max_width:
                words.append(chunk);chunk=''
            chunk+=char
        if chunk: words.append(chunk)
    lines=[]; line=''
    for w in words:
        test=f'{line} {w}'.strip()
        if draw.textbbox((0,0),test,font=font)[2] <= max_width or not line:
            line=test
        else:lines.append(line);line=w
    if line:lines.append(line)
    return lines

def _draw_title(draw,title,alpha=255):
    font_size=78
    while font_size >= 44:
        f=_choose_font(True,font_size)
        lines=_wrap(title.upper(),f,960,draw)
        if len(lines)<=4:break
        font_size-=4
    else:
        raise ValueError('Topic is too wide for the invitation. Please use a shorter title.')
    top=470
    for i,line in enumerate(lines):
        bounds=draw.textbbox((0,0),line,font=f)
        x=(1080-(bounds[2]-bounds[0]))//2
        draw.text((x,top+i*(font_size+18)),line,font=f,fill=(250,251,255,alpha))
    return top+len(lines)*(font_size+18)

def _base_background()->Image.Image:
    bg=Image.new('RGBA',(1080,1920),NAVY+(255,))
    draw=ImageDraw.Draw(bg,'RGBA')
    for y in range(1920):
        t=y/1920
        rgb=(int(8+15*(1-t)),int(10+9*(1-t)),int(27+35*(1-t)))
        draw.line([(0,y),(1079,y)],fill=rgb+(255,))
    draw.rounded_rectangle((60,80,1020,1840),radius=48,outline=(142,119,228,130),width=3)
    draw.rounded_rectangle((90,108,990,1810),radius=35,outline=(83,203,235,64),width=2)
    draw.ellipse((-260,50,430,790),fill=(71,38,145,22))
    draw.ellipse((650,1000,1400,1870),fill=(18,155,188,18))
    return bg

def _alpha_progress(now,start,length=.60):
    return max(0,min(1,(now-start)/length))

def build_gif(topic:str,brief:dict,venue:str='',
              date_label:str='',time_label:str='',
              fps:int=10,seconds:int=6)->bytes:
    """True 1080x1920 animated GIF with a global optimized palette. Free/local FFmpeg."""
    if not 4<=seconds<=12: raise ValueError('Duration must be between 4 and 12 seconds.')
    if not isinstance(fps,int) or isinstance(fps,bool) or not 1<=fps<=30:
        raise ValueError('FPS must be an integer between 1 and 30.')
    if not isinstance(seconds,int) or isinstance(seconds,bool):
        raise ValueError('Duration must be a whole number of seconds.')
    if not topic.strip() or len(topic)>110:
        raise ValueError('Topic must contain 1 to 110 characters.')
    venue=venue.strip() or 'TO BE ANNOUNCED'
    date_label=date_label.strip() or 'TO BE ANNOUNCED'
    time_label=time_label.strip() or 'TO BE ANNOUNCED'
    for value in (venue,date_label,time_label):
        if len(value)>60: raise ValueError('Event fields must be at most 60 characters.')
    base=_base_background()
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    num=fps*seconds
    with tempfile.TemporaryDirectory(prefix='talkline_gif_') as temp:
        for i in range(num):
            t=i/fps
            layer=Image.new('RGBA',(1080,1920),(0,0,0,0))
            d=ImageDraw.Draw(layer,'RGBA')
            # Changing accent strokes make the loop visibly animated.
            offset=int(34*math.sin(2*math.pi*t/seconds))
            d.rounded_rectangle((115+offset,275,965+offset,290),radius=7,fill=CYAN+(105,))
            a=int(255*_alpha_progress(t,.1))
            d.text((145,158),'TALKLINE  /  SPONTANEOUS TALK',font=_choose_font(True,29),fill=CYAN+(a,))
            a=int(255*_alpha_progress(t,.65))
            d.text((122,365),'NEXT EVENT',font=_choose_font(True,38),fill=(200,185,253,a))
            bottom=_draw_title(d,topic,alpha=a)
            a=int(255*_alpha_progress(t,1.8))
            if a:
                tag_font=_choose_font(False,32)
                tag_lines=_wrap(brief['tagline'],tag_font,840,d)
                if len(tag_lines)>3:
                    raise ValueError('Tagline does not fit the invitation. Please shorten it.')
                for j,line in enumerate(tag_lines):
                    d.text((140,max(920,bottom+80)+j*53),line,font=tag_font,fill=PALE+(a,))
            a=int(255*_alpha_progress(t,2.75))
            if a:
                d.rounded_rectangle((135,1200,945,1605),radius=35,fill=(27,32,65,int(a*.82)),outline=(85,210,232,int(a*.8)),width=2)
                items=[('LOCATION',venue),('DATE',date_label),('TIME',time_label)]
                for j,(label,value) in enumerate(items):
                    y=1240+j*116
                    d.text((175,y),label,font=_choose_font(True,25),fill=CYAN+(a,))
                    font=_choose_font(True,32)
                    lines=_wrap(value,font,720,d)
                    if len(lines)>2:
                        raise ValueError('Event text does not fit. Please shorten the event field.')
                    for row,line in enumerate(lines):
                        d.text((175,y+32+row*36),line,font=font,fill=WHITE+(a,))
            a=int(255*_alpha_progress(t,3.7))
            d.text((246,1704),'SPEAK  ·  CONNECT  ·  IMAGINE',font=_choose_font(True,27),fill=(192,172,255,a))
            frame=Image.alpha_composite(base,layer).convert('RGB')
            frame.save(f'{temp}/frame_{i:03d}.png',format='PNG')
        out=Path(temp)/'invitation.gif'
        filters='[0:v]split[a][b];[a]palettegen=max_colors=256:stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a'
        cmd=[ffmpeg,'-hide_banner','-loglevel','error','-y','-framerate',str(fps),
             '-i',str(Path(temp)/'frame_%03d.png'),'-filter_complex',filters,'-loop','0',str(out)]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        if result.returncode!=0:
            raise RuntimeError('FFmpeg GIF encoding failed: '+result.stderr[-900:])
        data=out.read_bytes()
    return data
