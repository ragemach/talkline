"""Local editor for one part of the Spontaneous Talk draft."""
from copy import deepcopy

import streamlit as st

from src.checkpoints import content_fingerprint
from src.spontaneous_content import validate_spontaneous


def edit_spontaneous(brief):
    with st.expander('Edit a section'):
        section = st.selectbox('Which part?', ['Opening and warm-up', 'Round 1 question',
                                              'Round 2 game card', 'Wrap-up'], key='edit_session_part')
        revision = content_fingerprint(brief)[:16]
        edited = deepcopy(brief)
        if section == 'Round 1 question':
            index = st.selectbox('Discussion card', range(len(brief['round1'])),
                                 format_func=lambda n: f"{n + 1}. {brief['round1'][n]['title']}")
            with st.form(f'session_edit_{revision}_discussion_{index}'):
                card = edited['round1'][index]
                card['title'] = st.text_input('Card title', value=card['title'], max_chars=32).strip()
                for level in ('a2', 'b2', 'c1'):
                    card[level] = st.text_area(f'{level.upper()} question', value=card[level],
                                               max_chars=115 if level == 'a2' else 165).strip()
                submitted = st.form_submit_button('Save question')
        elif section == 'Round 2 game card':
            level = st.selectbox('Playing level', ['elementary', 'advanced'], format_func=str.title)
            cards = brief['game'][level]
            index = st.selectbox('Game card', range(len(cards)),
                                 format_func=lambda n: f"{n + 1}. {cards[n]['title']}")
            with st.form(f'session_edit_{revision}_game_{level}_{index}'):
                card = edited['game'][level][index]
                fields = {'title': 'Card title', 'scenario': 'Glitch', 'choice_a': 'Patch A',
                          'outcome_a': 'Outcome A', 'choice_b': 'Patch B', 'outcome_b': 'Outcome B'}
                for field, label in fields.items():
                    card[field] = st.text_area(label, value=card[field], max_chars=240).strip()
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
            return validate_spontaneous(edited)
        except ValueError as exc:
            st.error(f'This edit could not be saved. {exc}')
            return None
