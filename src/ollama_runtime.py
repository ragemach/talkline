"""Start an installed local Ollama server when launching TalkLine; never install or pull."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]


def server_ready():
    # Loopback requests must not be routed through a system HTTP proxy.
    try:
        with build_opener(ProxyHandler({})).open('http://127.0.0.1:11434/api/version',timeout=1) as reply:
            data=json.load(reply)
        return isinstance(data,dict) and isinstance(data.get('version'),str)
    except (URLError,OSError,ValueError):
        return False


def find_ollama():
    executable=shutil.which('ollama')
    if executable:
        return Path(executable)
    local=os.environ.get('LOCALAPPDATA')
    if local:
        candidate=Path(local)/'Programs'/'Ollama'/'ollama.exe'
        if candidate.is_file(): return candidate
    return None


def ensure_local_server(timeout=12):
    if server_ready():
        return 'Ollama is already running locally.'
    executable=find_ollama()
    if executable is None:
        return 'Ollama is not installed. Demo mode is still available.'
    directory=ROOT/'user_data'
    directory.mkdir(exist_ok=True)
    env=dict(os.environ,OLLAMA_HOST='127.0.0.1:11434',OLLAMA_NO_CLOUD='1')
    models=directory/'ollama-models'
    if models.is_dir():
        env['OLLAMA_MODELS']=str(models)
    log_path=directory/'ollama-server.log'
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    with log_path.open('ab') as log:
        process=subprocess.Popen([str(executable),'serve'],env=env,stdout=log,
                                 stderr=subprocess.STDOUT,creationflags=flags)
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if server_ready():
            return 'Ollama started locally (cloud features disabled).'
        if process.poll() is not None:
            # Another concurrent launcher may have acquired the port.
            if server_ready(): return 'Ollama is running locally.'
            raise RuntimeError(f'Ollama exited before becoming ready. See {log_path}')
        time.sleep(.25)
    raise RuntimeError(f'Ollama is taking longer to start. See {log_path}. Demo remains available.')
