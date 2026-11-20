"""Run both Game Night activities from their generated standalone files."""

import json
import re

import pytest

from src.game_night_export import build_game_night_game
from test_game_content import fixture_game
from test_game_export import _check_browser_game


def test_game_night_output_escapes_content_and_validates_decks():
    game = fixture_game('taboo')
    game['title'] = 'Taboo & friends'
    word = '</script><script>unexpected()</script>'
    game['elementary'][0]['word'] = word
    page = build_game_night_game('Play <together>', game)
    assert word not in page
    assert '<h1>Taboo &amp; friends</h1>' in page
    assert '<p>Play &lt;together&gt;</p>' in page
    data = json.loads(re.search(r'id="game-data" type="application/json">(.*?)</script>', page).group(1))
    assert data['decks']['elementary'][0]['word'] == word
    assert len(data['decks']['elementary']) == len(data['decks']['advanced']) == 20
    game['advanced'].pop()
    with pytest.raises(ValueError, match='advanced'):
        build_game_night_game('Play together', game)
    with pytest.raises(ValueError, match='supports Taboo and Problem Solver'):
        build_game_night_game('Play together', fixture_game('patch_notes'))


def _browser_result(tmp_path, mechanic, checks):
    html = build_game_night_game('Fun in the city', fixture_game(mechanic))
    setup = r'''
    function click(id) {
      const button = element(id);
      check(button.offsetWidth > 0 && !button.disabled, id + ' is not available');
      button.click();
    }
    function shown(id) { return element(id).offsetWidth > 0; }
    function text(id) { return element(id).textContent; }
    check(!shown('play'), 'Choose a level first');
    '''
    _check_browser_game(tmp_path, html, setup + checks)


def test_taboo_timer_scoring_visibility_and_level_resume(tmp_path):
    _browser_result(tmp_path, 'taboo', r'''
    let testTime = 0;
    Date.now = () => testTime;
    click('elementary');
    check(!shown('taboo-card') && !text('target-word'), 'Card starts private');
    click('start-turn');
    check(text('target-word') === 'word 0', 'First Elementary word');
    check(element('forbidden').children.length === 3, 'Display every supplied forbidden clue');
    click('reveal-card');
    check(!shown('taboo-card') && !text('target-word'), 'Hide target from guessers');
    click('reveal-card');
    click('correct');
    check(text('score-a') === '1' && text('target-word') === 'word 1', 'Correct advances and scores for A');
    click('forbidden-word');
    click('skip');
    check(text('score-a') === '1' && text('target-word') === 'word 3', 'Lost and skipped cards both advance');
    testTime += 10000;
    click('advanced');
    check(text('score-a') === '0', 'Scores remain separate by level');
    testTime += 100000;
    click('elementary');
    check(text('timer') === '50 seconds left · Paused', 'Level switch pauses the clock');
    check(!shown('taboo-card') && text('score-a') === '1', 'Pausing hides clues and keeps points');
    click('start-turn');
    check(text('target-word') === 'word 3', 'Resume the same card');
    testTime += 50000;
    updateTimer();
    check(text('taboo-team') === 'Team B gives clues' && !shown('correct'), 'Time expires and switches the team');
    click('start-turn');
    click('correct');
    check(text('score-b') === '1', 'Team B scores');
    click('end-turn');
    click('restart');
    check(text('score-a') === '0' && text('score-b') === '0', 'Restart clears the active level');

    for (const [level, start] of [['elementary', 0], ['advanced', 20]]) {
      click(level);
      element('duration').value = '0';
      element('duration').dispatchEvent(new Event('change'));
      click('start-turn');
      check(text('timer') === 'Untimed turn', 'Host may choose an untimed turn');
      for (let index = start; index < start + 20; index += 1) {
        check(text('target-word') === 'word ' + index, 'Every Taboo card plays');
        check(document.querySelector('main').scrollWidth <= 375, 'Taboo fits at phone width');
        click('correct');
      }
      check(shown('finish') && text('winner') === 'Team A wins!', 'Show winner after all cards');
      click('restart');
      check(!shown('finish') && text('score-a') === '0', 'Replay resets scores');
    }
    ''')


def test_problem_solver_alternates_presenter_and_opponent_scoring(tmp_path):
    _browser_result(tmp_path, 'problem_solver', r'''
    for (const [level, start] of [['elementary', 0], ['advanced', 20]]) {
      click(level);
      const totals = [0, 0];
      for (let offset = 0; offset < 20; offset += 1) {
        const team = offset % 2;
        const presenter = team ? 'Team B' : 'Team A';
        const scorer = team ? 'Team A' : 'Team B';
        check(text('problem-title') === 'problem ' + (start + offset), 'Every problem is shown in order');
        check(text('problem-team') === presenter + ' presents a solution.', 'Presenters alternate');
        check(!shown('points') && shown('present'), 'Prepare before opening scores');
        click('present');
        check(shown('points') && text('point-scorer') === scorer + ' awards points', 'Other team awards points');
        check(document.querySelector('main').scrollWidth <= 375, 'Problem Solver fits at phone width');
        const points = offset % 3 + 1;
        totals[team] += points;
        click('point-' + points);
        check(Number(text('score-a')) === totals[0] && Number(text('score-b')) === totals[1],
              'Points count for the presenter');
      }
      check(shown('finish') && !shown('problem-solver'), 'Finish once all problems are scored');
    }
    click('elementary');
    check(shown('finish'), 'Keep completed state when changing level');
    click('restart');
    check(text('problem-title') === 'problem 0' && text('score-a') === '0', 'Replay starts a new match');
    ''')
