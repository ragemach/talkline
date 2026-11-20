from unittest.mock import Mock, patch
from pathlib import Path
import pytest
from src.ollama_runtime import ensure_local_server


def test_running_server_is_reused_without_spawning():
    with patch('src.ollama_runtime.server_ready',return_value=True), \
         patch('src.ollama_runtime.subprocess.Popen') as process:
        assert 'already' in ensure_local_server()
        process.assert_not_called()


def test_no_install_does_not_block_demo():
    with patch('src.ollama_runtime.server_ready',return_value=False), \
         patch('src.ollama_runtime.find_ollama',return_value=None):
        assert 'Demo' in ensure_local_server()


def test_installed_server_starts_with_local_only_environment(tmp_path):
    (tmp_path/'user_data'/'ollama-models').mkdir(parents=True)
    with patch('src.ollama_runtime.ROOT',tmp_path), \
         patch('src.ollama_runtime.server_ready',side_effect=[False,True]), \
         patch('src.ollama_runtime.find_ollama',return_value=Path('ollama.exe')), \
         patch('src.ollama_runtime.subprocess.Popen') as process:
        assert 'started' in ensure_local_server()
        options=process.call_args.kwargs
        assert options['env']['OLLAMA_NO_CLOUD']=='1'
        assert options['env']['OLLAMA_HOST']=='127.0.0.1:11434'
        assert options['env']['OLLAMA_MODELS']==str(tmp_path/'user_data'/'ollama-models')
        assert process.call_args.args[0]==['ollama.exe','serve']


def test_early_server_exit_reports_log(tmp_path):
    with patch('src.ollama_runtime.ROOT',tmp_path), \
         patch('src.ollama_runtime.server_ready',return_value=False), \
         patch('src.ollama_runtime.find_ollama',return_value=Path('ollama.exe')), \
         patch('src.ollama_runtime.subprocess.Popen',return_value=Mock(poll=Mock(return_value=1))):
        with pytest.raises(RuntimeError,match='ollama-server.log'): ensure_local_server()
