"""Edit one part of a full session without regenerating the rest."""
from copy import deepcopy

import streamlit as st

from src.checkpoints import content_fingerprint
from src.content_rules import ROUND_CARD_TEXT_LIMITS


def edit_session(brief, validate):
    with st.expander('Edit a section'):
        sections = ['Opening and warm-up']
        if 'round1' in brief:
            sections.append('Round 1 question')
        else:
            sections.append('Round 1 game card')
        sections.extend(['Round 2 game card', 'Wrap-up'])
        section = st.selectbox('Which part?', sections, key='edit_session_part')
        revision = content_fingerprint(brief)[:16]
        edited = deepcopy(brief)
        if section == 'Round 1 question':
            index = st.selectbox('Discussion card', range(len(brief['round1'])),
                                 format_func=lambda n: f"{n + 1}. {brief['round1'][n]['title']}")
            with st.form(f'session_edit_{revision}_discussion_{index}'):
                card = edited['round1'][index]
                card['title'] = st.text_input('Card title', value=card['title'], max_chars=32).strip()
                for level, limit in ROUND_CARD_TEXT_LIMITS.items():
                    card[level] = st.text_area(f'{level.upper()} question', value=card[level],
                                               max_chars=limit).strip()
                submitted = st.form_submit_button('Save question')
        elif section.endswith('game card'):
            if 'games' in edited:
                round_index = 0 if section.startswith('Round 1') else 1
                game = edited['games'][round_index]
            else:
                game = edited['game']
            mechanic = game['mechanic']
            identity = 'word' if mechanic == 'taboo' else 'title'
            level = st.selectbox('Playing level', ['elementary', 'advanced'], format_func=str.title)
            cards = game[level]
            index = st.selectbox('Game card', range(len(cards)),
                                 format_func=lambda n: f"{n + 1}. {cards[n][identity]}")
            with st.form(f'session_edit_{revision}_{mechanic}_{level}_{index}'):
                _edit_game_fields(cards[index], mechanic)
                submitted = st.form_submit_button('Save game card')
        elif section == 'Opening and warm-up':
            with st.form(f'session_edit_{revision}_opening'):
                edited['opening'] = st.text_area('Opening paragraph', value=brief['opening'], max_chars=250).strip()
                edited['warmup'] = [st.text_input(f'Warm-up question {n}', value=question, max_chars=48).strip()
                                    for n, question in enumerate(brief['warmup'], 1)]
                submitted = st.form_submit_button('Save opening and warm-up')
        else:
            with st.form(f'session_edit_{revision}_closing'):
                edited['closing'] = st.text_area('Closing paragraph', value=brief['closing'], max_chars=250).strip()
                submitted = st.form_submit_button('Save wrap-up')
        if not submitted:
            return None
        try:
            return validate(edited)
        except ValueError as exc:
            st.error(f'This edit could not be saved. {exc}')
            return None


def _edit_game_fields(card, mechanic):
    if mechanic == 'taboo':
        card['word'] = st.text_input('Target word', value=card['word'], max_chars=70).strip()
        card['forbidden'] = [
            st.text_input(f'Forbidden clue {index}', value=clue, max_chars=70).strip()
            for index, clue in enumerate(card['forbidden'], 1)
        ]
        return
    if mechanic == 'problem_solver':
        fields = {'title': ('Card title', 70), 'situation': ('Situation', 240), 'challenge': ('Challenge', 240)}
    else:
        scenario, first, second = ('Glitch', 'Patch A', 'Patch B') if mechanic == 'patch_notes' else (
            'Situation', 'Smart argument', 'Sneaky argument')
        fields = {'title': ('Card title', 240), 'scenario': (scenario, 240),
                  'choice_a': (first, 240), 'outcome_a': ('Outcome A', 240),
                  'choice_b': (second, 240), 'outcome_b': ('Outcome B', 240)}
    for field, (label, limit) in fields.items():
        card[field] = st.text_area(label, value=card[field], max_chars=limit).strip()
