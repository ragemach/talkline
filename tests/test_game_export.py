"""Exercise the standalone Patch Notes export in addition to its data contract."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.game_export import build_leveled_patch_game, build_patch_game, build_smart_or_sneaky_game


def _card(level, index):
    return {
        'title': f'{level} idea {index}',
        'scenario': f'Unexpected change {level} {index}.',
        'choice_a': 'Discuss the change with a friend.',
        'choice_b': 'Make a poster about the change.',
        'outcome_a': f'{level} {index} starts a conversation.',
        'outcome_b': f'{level} {index} attracts a crowd.',
    }


def _game():
    return {
        'mechanic': 'patch_notes',
        'title': 'Patch <Notes>',
        'rules': ['Read the <glitch>.', 'Compare both patches.', 'Choose one.', 'Keep or reset.'],
        'elementary': [_card('Elementary', index) for index in range(1, 21)],
        'advanced': [_card('Advanced', index) for index in range(1, 21)],
    }


def _embedded_cards(html):
    return json.loads(re.search(r'<script id="cards" type="application/json">(.*?)</script>', html).group(1))


def test_leveled_export_maps_all_cards_and_escapes_model_text():
    game = _game()
    scenario = 'A sign says </script><script>throw Error("unsafe")</script>.'
    game['elementary'][0]['scenario'] = scenario
    html = build_leveled_patch_game('A café & park', game)
    payload = _embedded_cards(html)

    assert scenario not in html
    assert 'A café &amp; park' in html
    assert '<h1>Patch &lt;Notes&gt;</h1>' in html
    assert '<li>Read the &lt;glitch&gt;.</li>' in html
    assert len(payload['elementary']) == len(payload['advanced']) == 20
    assert payload['elementary'][0]['glitch'] == scenario
    assert payload['advanced'][-1]['patch_b'] == game['advanced'][-1]['choice_b']
    assert payload['advanced'][-1]['consequence_a'] == game['advanced'][-1]['outcome_a']


def test_prototype_still_embeds_a_single_deck():
    cards = [{
        'title': 'Prototype',
        'glitch': 'The sign keeps changing.',
        'patch_a': 'Paint the sign.',
        'patch_b': 'Use a small printed sign.',
        'consequence_a': 'Everyone can see it.',
        'consequence_b': 'People have to walk closer.',
    }]
    assert _embedded_cards(build_patch_game('Demo', cards)) == cards


def _headless_browser():
    candidates = [shutil.which(name) for name in ('msedge', 'chromium', 'chromium-browser', 'google-chrome')]
    for variable in ('PROGRAMFILES(X86)', 'PROGRAMFILES', 'LOCALAPPDATA'):
        directory = os.environ.get(variable)
        if directory:
            candidates += [
                Path(directory) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
                Path(directory) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
            ]
    return next((str(path) for path in candidates if path and Path(path).is_file()), None)


def _check_browser_game(tmp_path, html, checks):
    browser = _headless_browser()
    if browser is None:
        pytest.skip('A local Chromium browser is needed for this check.')
    setup = '''
    const check = (condition, message) => {
      if (!condition) throw new Error(message);
    };
    document.body.style.width = '375px';
    '''
    exercise = ('<script>try {' + setup + checks +
                "document.body.dataset.testResult = ['talkline', 'pass'].join('-');"
                '} catch (error) { document.body.dataset.testResult = error.message; }</script>')
    page = tmp_path / 'game.html'
    page.write_text(html.replace('</body>', exercise + '</body>'), encoding='utf-8')
    result = subprocess.run(
        [browser, '--headless=new', '--disable-gpu', '--no-first-run', '--disable-extensions',
         '--disable-background-networking', f'--user-data-dir={tmp_path / "profile"}',
         '--dump-dom', page.as_uri()],
        timeout=40,
        capture_output=True,
        encoding='utf-8',
        errors='replace',
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
    )
    body = re.search(r'<body[^>]*>', result.stdout)
    assert result.returncode == 0, result.stderr
    assert body and 'data-test-result="talkline-pass"' in body.group(0), (body and body.group(0), result.stderr)


def test_play_both_levels_in_a_local_browser(tmp_path):
    checks = '''
      check(element('card').hidden && !element('level-controls').hidden, 'Choose a level first');
      element('advanced').click();
      element('patch-b').click();
      check(!element('decisions').hidden && element('next').disabled, 'Resolve patch before advancing');
      element('keep').click();
      element('next').click();
      element('elementary').click();
      check(element('title').textContent === 'Elementary idea 1', 'New level starts at card 1');
      element('advanced').click();
      check(element('title').textContent === 'Advanced idea 2', 'Switching keeps progress');
      element('back').click();
      check(element('consequence').textContent === 'Advanced 1 attracts a crowd.', 'Back keeps outcome');
      check(!element('feedback').hidden, 'Back keeps decision');
      element('restart').click();
      check(element('outcome').hidden && element('next').disabled, 'Restart clears decisions');

      for (const [name, label] of [['elementary', 'Elementary'], ['advanced', 'Advanced']]) {
        element(name).click();
        check(element(name).getAttribute('aria-pressed') === 'true', 'Active level is announced');
        for (let card = 1; card <= 20; card += 1) {
          const a = card % 2 !== 0;
          check(element('title').textContent === label + ' idea ' + card, 'Correct card in level');
          check(element('outcome').hidden && !element('consequence').textContent, 'Outcomes stay hidden');
          check(element('next').disabled, 'Choose a patch before advancing');
          element(a ? 'patch-a' : 'patch-b').click();
          const outcome = a ? ' starts a conversation.' : ' attracts a crowd.';
          check(element('consequence').textContent === label + ' ' + card + outcome, 'Only chosen outcome');
          check(element('next').disabled, 'Choose keep or reset before advancing');
          element(a ? 'keep' : 'reset').click();
          check(!element('next').disabled, 'Decision unlocks advance');
          check(document.querySelector('main').scrollWidth <= 375, 'No horizontal card overflow');
          element('next').click();
        }
        check(!element('finished').hidden, 'Finish after 20 cards');
        check(element('restart').textContent === 'Play again', 'Offer replay');
        element('restart').click();
        check(element('title').textContent === label + ' idea 1', 'Replay starts from first card');
      }
    '''
    _check_browser_game(tmp_path, build_leveled_patch_game('A café & park', _game()), checks)


def test_smart_or_sneaky_shows_a_verdict_twist_without_patch_controls(tmp_path):
    game = _game()
    game['mechanic'] = 'smart_or_sneaky'
    game['title'] = 'Smart or Sneaky?'
    game['rules'] = [
        'Read the marketing move.', 'Explain both verdicts.',
        'Choose a verdict and reveal the twist.', 'Would you change your mind?',
    ]
    html = build_smart_or_sneaky_game('Marketing', game)
    checks = '''
    for (const [level, label] of [['elementary', 'Elementary'], ['advanced', 'Advanced']]) {
      element(level).click();
      for (let card = 1; card <= 20; card += 1) {
        const smart = card % 2 !== 0;
        check(element('patch-a').textContent.startsWith('Smart move:'), 'Smart verdict label');
        check(element('patch-b').textContent.startsWith('Sneaky trick:'), 'Sneaky verdict label');
        check(element('outcome').hidden && element('next').disabled, 'Twist starts hidden');
        element(smart ? 'patch-a' : 'patch-b').click();
        const twist = smart ? ' starts a conversation.' : ' attracts a crowd.';
        check(element('result-title').textContent === 'Plot twist', 'Explain the twist');
        check(element('consequence').textContent === label + ' ' + card + twist, 'Reveal chosen twist');
        check(!element('feedback').hidden && element('feedback').textContent === 'Would you change your mind?',
              'Encourage discussion after reveal');
        check(element('decisions').hidden && !element('next').disabled, 'Next without Keep or Reset');
        check(document.querySelector('main').scrollWidth <= 375, 'Fits at phone width');
        element('next').click();
      }
      check(!element('finished').hidden, 'Complete the deck');
      element('restart').click();
      check(element('outcome').hidden, 'Replay resets twists');
    }
    '''
    _check_browser_game(tmp_path, html, checks)
