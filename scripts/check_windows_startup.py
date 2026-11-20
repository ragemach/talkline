"""Exercise the actual batch launcher, check HTTP health, then stop only its process tree."""
from pathlib import Path
import os
import subprocess
import time
from urllib.request import urlopen
from urllib.error import URLError


def main():
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, STREAMLIT_SERVER_HEADLESS='true')
    log_path = root / 'output' / 'startup.log'
    log_path.parent.mkdir(exist_ok=True)
    try:
        with urlopen('http://127.0.0.1:8501/_stcore/health', timeout=1):
            raise RuntimeError('Port 8501 already has a server. Close it before this check.')
    except URLError:
        pass
    with log_path.open('w', encoding='utf-8') as log:
        process = subprocess.Popen(['cmd', '/c', 'START_WINDOWS.bat'], cwd=root,
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(40):
                if process.poll() is not None:
                    raise RuntimeError(f'Launcher exited: see {log_path}')
                try:
                    with urlopen('http://127.0.0.1:8501/_stcore/health', timeout=1) as response:
                        assert response.read() == b'ok'
                    print('PASS: START_WINDOWS.bat starts healthy local Streamlit on port 8501.')
                    break
                except URLError:
                    time.sleep(.5)
            else:
                raise RuntimeError(f'Startup timeout: see {log_path}')
        finally:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, check=False)
            process.wait(timeout=10)


if __name__ == '__main__':
    main()
