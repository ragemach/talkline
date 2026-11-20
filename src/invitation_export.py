"""Local rendering of original invitation shapes; no replacement layout or artwork."""
from io import BytesIO
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import math
from PIL import Image, ImageEnhance, ImageFont
import pypdfium2 as pdfium

ROOT=Path(__file__).resolve().parents[1]


def install_bundled_fonts():
    if os.name!='nt': return
    import winreg
    import ctypes
    directory=Path(os.environ['LOCALAPPDATA'])/'Microsoft/Windows/Fonts'
    directory.mkdir(parents=True,exist_ok=True)
    changed=False
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows NT\CurrentVersion\Fonts') as key:
        for source in (ROOT/'assets/fonts').glob('*.ttf'):
            target=directory/source.name
            if target.exists() and target.read_bytes()!=source.read_bytes():
                raise RuntimeError(f'A different font already exists at {target}. No font was overwritten.')
            copied=not target.exists()
            if copied: shutil.copyfile(source,target)
            family,style=ImageFont.truetype(str(source),20).getname()
            name=f'{family} {style} (TrueType)'
            try: registered=winreg.QueryValueEx(key,name)[0]==str(target)
            except FileNotFoundError: registered=False
            if copied or not registered:
                winreg.SetValueEx(key,name,0,winreg.REG_SZ,str(target))
                ctypes.windll.gdi32.AddFontResourceExW(str(target),0,0)
                changed=True
    if changed: ctypes.windll.user32.SendNotifyMessageW(0xFFFF,0x001D,0,0)


def libreoffice_executable():
    found=shutil.which('soffice.com') or shutil.which('soffice')
    if found: return found
    for variable in ('PROGRAMFILES','PROGRAMFILES(X86)'):
        if os.environ.get(variable):
            candidate=Path(os.environ[variable])/'LibreOffice/program/soffice.com'
            if candidate.exists(): return str(candidate)
    raise RuntimeError('LibreOffice is required for rendering the original invitation. Install the free Windows version once.')


def render_invitation(pptx_bytes,long_edge=1920):
    if not isinstance(long_edge,int) or not 700<=long_edge<=2400:
        raise ValueError('Preview resolution must be between 700 and 2400 pixels.')
    install_bundled_fonts()
    executable=libreoffice_executable()
    with tempfile.TemporaryDirectory(prefix='talkline_invitation_') as directory:
        root=Path(directory)
        source=root/'invitation.pptx'
        source.write_bytes(pptx_bytes)
        command=[executable,f'-env:UserInstallation={(root/"lo-profile").as_uri()}',
                 '--headless','--convert-to','pdf','--outdir',str(root),str(source)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=180,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        target=root/'invitation.pdf'
        if result.returncode or not target.exists():
            raise RuntimeError('Invitation rendering failed: '+(result.stderr or result.stdout)[-700:])
        with pdfium.PdfDocument(target) as document:
            if len(document)!=1: raise ValueError('An invitation must contain exactly one selected source slide.')
            page=document[0]
            width,height=page.get_size()
            bitmap=page.render(scale=long_edge/max(width,height))
            image=bitmap.to_pil().convert('RGB').copy()
            bitmap.close()
            page.close()
    return image


def animate_invitation(image,seconds=8,fps=10):
    """Subtle exposure fade with a six-second unchanged hold and a seamless loop.

    Every frame uses the same source composition. No shapes move or get added.
    GIF palette quantization is lossy; the accompanying PNG retains the RGB render.
    """
    if seconds!=8 or fps!=10: raise ValueError('This animation preset is eight seconds at ten FPS.')
    base=image.convert('RGB')
    # One palette shared by every frame avoids flashing colors.
    palette=base.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    frames=[]
    for i in range(seconds*fps):
        t=i/fps
        if t<1: factor=.96+.04*(1-math.cos(math.pi*t))/2
        elif t>=7: factor=.96+.04*(1+math.cos(math.pi*(t-7)))/2
        else: factor=1
        frame=base if factor==1 else ImageEnhance.Brightness(base).enhance(factor)
        frames.append(frame.quantize(palette=palette,dither=Image.Dither.FLOYDSTEINBERG))
    output=BytesIO()
    frames[0].save(output,format='GIF',save_all=True,append_images=frames[1:],
                   duration=100,loop=0,optimize=False,disposal=1)
    return output.getvalue()
