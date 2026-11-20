from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ollama_runtime import ensure_local_server

if __name__=='__main__':
    try:
        print(ensure_local_server())
    except (RuntimeError,OSError) as exc:
        print(f'Local AI startup warning: {exc}')
        # A missing or slow AI server must not prevent offline Demo use.
