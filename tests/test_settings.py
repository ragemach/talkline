import json
from unittest.mock import patch
import pytest
from src.settings import EventDetails, UserSettings, load_settings, save_settings


def test_no_assumed_metadata_and_unicode_roundtrip(tmp_path):
    path=tmp_path/'settings.json'
    assert load_settings(path)==UserSettings()
    settings=UserSettings(EventDetails('  Beşiktaş · کافه  ','','19:45'))
    save_settings(settings,path)
    assert load_settings(path)==settings
    assert settings.event.venue=='Beşiktaş · کافه'
    assert settings.event.date==''


@pytest.mark.parametrize('kwargs',[
    {'venue':None},{'time':'x'*61},{'feedback_url':'javascript:alert(1)'},
    {'feedback_url':'https://'}, {'feedback_url':'https://a.test/my link'}])
def test_invalid_metadata_rejected(kwargs):
    with pytest.raises(ValueError): EventDetails(**kwargs)


def test_corrupt_settings_are_reported_and_preserved(tmp_path):
    path=tmp_path/'settings.json'
    path.write_text('{broken',encoding='utf-8')
    with pytest.raises(ValueError,match='not been overwritten'): load_settings(path)
    assert path.read_text()=='{broken'


def test_atomic_save_failure_retains_previous_defaults(tmp_path):
    path=tmp_path/'settings.json'
    save_settings(UserSettings(),path)
    before=path.read_bytes()
    with patch('src.settings.os.replace',side_effect=OSError('disk error')):
        with pytest.raises(OSError): save_settings(UserSettings(EventDetails('new venue')),path)
    assert path.read_bytes()==before
    assert not list(tmp_path.glob('*.tmp'))


def test_cloud_model_preference_is_rejected():
    with pytest.raises(ValueError,match='cloud'): UserSettings(model='gpt-oss:120b-cloud')
