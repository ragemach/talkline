"""TalkLine Studio's local session workspace."""
from __future__ import annotations
import json
import hashlib
import zipfile
from html import escape
from io import BytesIO
import streamlit as st
from src.ai_content import available_models, create_with_ollama, review_brief, regenerate_section, repair_reviewed_brief
from src.business_content import generate_business, regenerate_business_section, validate_business
from src.game_night_content import generate_game_night, validate_game_night
from src.invitation_content import LABELS, detect_category
from src.settings import EventDetails, UserSettings, load_settings, save_settings
from src.toolkit import generate_toolkit, LEVEL_LABELS
from src.toolkit_export import toolkit_html
from src.toolkit_library import sample_toolkit
from src.toolkit_pptx import build_toolkit_pptx
from src.checkpoints import (
    clear_session_progress, content_fingerprint, load_automatic_concept, load_session_progress, save_session_progress,
)
from src.run_state import (
    DEMO_MODE, LOCAL_MODE, draft_from_state, export_revision,
    set_event_widgets, set_toolkit, toolkit_for_event, validate_draft,
)
from src.run_store import load_run, save_run
from src.host_guide import HOST_GUIDE_FILENAME
from src.session_export import build_session_export
from src.session_editor import edit_session
from src.spontaneous_content import generate_spontaneous, regenerate_spontaneous_section, validate_spontaneous
from src.session_sequence import (
    FULL_BUSINESS, FULL_GAME_NIGHT, FULL_SPONTANEOUS, FULL_WORKFLOWS, TOOLKIT_HTML_FILENAME,
    TOOLKIT_PPTX_FILENAME, build_session_sequence, game_filenames, presentation_filename,
)

SESSION_GENERATORS = {
    FULL_SPONTANEOUS: generate_spontaneous, FULL_BUSINESS: generate_business, FULL_GAME_NIGHT: generate_game_night,
}
SESSION_VALIDATORS = {
    FULL_SPONTANEOUS: validate_spontaneous, FULL_BUSINESS: validate_business, FULL_GAME_NIGHT: validate_game_night,
}
SECTION_REGENERATORS = {
    FULL_SPONTANEOUS: regenerate_spontaneous_section, FULL_BUSINESS: regenerate_business_section,
}


def save_current_run():
    draft = draft_from_state(st.session_state)
    revision = export_revision(draft)
    package = st.session_state.get('package')
    if revision != st.session_state.get('package_revision'):
        package = None
        st.session_state.pop('package', None)
        st.session_state.pop('package_revision', None)
    try:
        save_run(draft, package=package, export_revision=revision if package else None)
    except (ValueError, OSError) as exc:
        st.session_state['run_save_warning'] = (
            f'This work is open but could not be saved locally. Your previous save is still on disk. {exc}'
        )
        return False
    else:
        st.session_state.pop('run_save_warning', None)
        return True


def restore_run_once():
    if st.session_state.get('run_loaded'):
        return
    st.session_state['run_loaded'] = True
    try:
        saved = load_run()
        if saved is None:
            return
        validate_draft(saved.draft)
    except (ValueError, OSError) as exc:
        st.session_state['run_restore_warning'] = f'Could not reopen the saved run. {exc}'
        return
    st.session_state.update(saved.draft)
    set_event_widgets(st.session_state)
    st.session_state['run_restored'] = True
    if saved.warning:
        st.session_state['run_restore_warning'] = saved.warning
    if saved.package is not None:
        try:
            if saved.export_revision != export_revision(saved.draft):
                raise ValueError('The ZIP belongs to a different version of the saved work.')
            with zipfile.ZipFile(BytesIO(saved.package)) as archive:
                metadata = saved.draft['metadata']
                required = {presentation_filename(metadata), *game_filenames(metadata), HOST_GUIDE_FILENAME, 'content.json',
                            'TalkLine_Invitation.gif', 'TalkLine_Invitation.png', 'TalkLine_Invitation.pptx'}
                if toolkit_for_event(saved.draft) is not None:
                    required.add(TOOLKIT_HTML_FILENAME)
                    if metadata.get('workflow') not in FULL_WORKFLOWS.values():
                        required.add(TOOLKIT_PPTX_FILENAME)
                if not required <= set(archive.namelist()) or archive.testzip() is not None:
                    raise ValueError('The saved ZIP is incomplete or damaged.')
                size = tuple(json.loads(archive.read('content.json'))['invitation']['size'])
                if len(size) != 2 or any(type(dimension) is not int or dimension <= 0 for dimension in size):
                    raise ValueError('The saved invitation size is invalid.')
        except (zipfile.BadZipFile, KeyError, TypeError, ValueError, OSError) as exc:
            st.session_state['run_restore_warning'] = f'Saved work recovered. Build a fresh ZIP. {exc}'
        else:
            st.session_state['invitation_size'] = size
            st.session_state['package'] = saved.package
            st.session_state['package_revision'] = saved.export_revision


def automatic_concept(topic, model):
    if not topic:
        return None
    saved = st.session_state.get('metadata', {})
    if saved.get('topic') == topic and saved.get('concept_selection') == 'auto':
        return saved['concept']
    if not model:
        return None
    key = (topic, model)
    if st.session_state.get('suggestion_key') != key:
        concept = load_automatic_concept(topic, model)
        if concept is None:
            with st.spinner('Choosing a session concept…'):
                concept = detect_category(topic, model)
        st.session_state['suggestion_key'] = key
        st.session_state['suggested_concept'] = concept
    return st.session_state['suggested_concept']


def start_new_topic(previous_topic):
    saved = st.session_state.get('metadata', {})
    if (previous_topic.strip() == saved.get('topic') and
            st.session_state['topic_input'].strip() != saved['topic'] and
            st.session_state.get('concept_input') == saved.get('concept')):
        st.session_state['concept_input'] = 'auto'


def discussion_preview(card):
    """Separate a shared scene only when removing it preserves every tier's wording."""
    tiers = {level: card[level] for level in ('a2', 'b2', 'c1')}
    scene, separator, question = tiers['a2'].rpartition('. ')
    prefix = scene + separator
    if scene and question.split(' ', 1)[0].casefold() in ('what', 'which', 'who', 'where', 'when', 'why', 'how'):
        if all(value.startswith(prefix) and value[len(prefix):].strip() for value in tiers.values()):
            return scene + '.', {level: value[len(prefix):] for level, value in tiers.items()}
    return '', tiers


st.set_page_config(page_title='TalkLine Studio',page_icon='⚡',layout='centered')
restore_run_once()
st.markdown('''<style>
/* TalkLine Studio Modern Design System */
:root {
  --tl-navy: #0F172A;
  --tl-slate: #1E293B;
  --tl-primary: #4F46E5;
  --tl-primary-hover: #4338CA;
  --tl-primary-light: #EEF2FF;
  --tl-border: #E2E8F0;
  --tl-bg: #F8FAFC;
  --tl-card: #FFFFFF;
}

html, body, [class*="css"] {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
}

.stApp {
  background-color: var(--tl-bg) !important;
}

h1 {
  font-weight: 800 !important;
  letter-spacing: -0.025em !important;
  color: #0F172A !important;
  font-size: 2.1rem !important;
  margin-bottom: 0.2rem !important;
}

[data-testid="stCaptionContainer"] {
  color: #64748B !important;
  font-size: 0.95rem !important;
  font-weight: 500 !important;
}

.tl-status-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin: 8px 0 16px 0;
  padding: 8px 12px;
  background: #FFFFFF;
  border: 1px solid var(--tl-border);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

.tl-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 600;
}

.tl-pill-green { background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; }
.tl-pill-red { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
.tl-pill-indigo { background: #EEF2FF; color: #3730A3; border: 1px solid #C7D2FE; }
.tl-pill-blue { background: #F0FDF4; color: #166534; border: 1px solid #BBF7D0; }
.tl-pill-gray { background: #F1F5F9; color: #475569; border: 1px solid #E2E8F0; }

div[data-testid="stTextInput"] input {
  border-radius: 10px !important;
  border: 1.5px solid var(--tl-border) !important;
  padding: 10px 14px !important;
  font-size: 1rem !important;
  background: #FFFFFF !important;
  transition: all 0.2s ease !important;
}

div[data-testid="stTextInput"] input:focus {
  border-color: var(--tl-primary) !important;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15) !important;
}

button[kind="primary"] {
  background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 10px !important;
  padding: 10px 22px !important;
  font-weight: 600 !important;
  letter-spacing: 0.01em !important;
  box-shadow: 0 4px 12px 0 rgba(79, 70, 229, 0.3) !important;
  transition: all 0.2s ease !important;
}

button[kind="primary"]:hover:not(:disabled) {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 18px 0 rgba(79, 70, 229, 0.4) !important;
}

button[kind="primary"]:disabled {
  opacity: 0.55 !important;
  box-shadow: none !important;
}

button[kind="secondary"], [data-testid="stDownloadButton"] button {
  border-radius: 10px !important;
  border: 1.5px solid var(--tl-border) !important;
  background: #FFFFFF !important;
  font-weight: 600 !important;
  color: var(--tl-slate) !important;
  transition: all 0.2s ease !important;
}

button[kind="secondary"]:hover, [data-testid="stDownloadButton"] button:hover {
  border-color: var(--tl-primary) !important;
  color: var(--tl-primary) !important;
  background: var(--tl-primary-light) !important;
}

div[data-testid="stExpander"] {
  background: #FFFFFF !important;
  border: 1px solid var(--tl-border) !important;
  border-radius: 12px !important;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.02) !important;
  margin-bottom: 14px !important;
}

div[data-testid="stExpander"] summary {
  font-weight: 600 !important;
  color: var(--tl-navy) !important;
}

.tl-round-card {
  background: #FFFFFF;
  border: 1px solid var(--tl-border);
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 14px;
  box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.03);
}

.tl-card-scene {
  background: #F1F5F9;
  border-left: 4px solid #4F46E5;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.95rem;
  color: #1E293B;
  margin-bottom: 12px;
  font-weight: 500;
}

.tl-tier-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 8px 0;
  font-size: 0.93rem;
  line-height: 1.45;
  border-bottom: 1px solid #F8FAFC;
}

.tl-tier-row:last-child {
  border-bottom: none;
}

.tl-tier-badge {
  flex-shrink: 0;
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.tl-tier-a2 { background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; }
.tl-tier-b2 { background: #EFF6FF; border: 1px solid #BFDBFE; color: #1E40AF; }
.tl-tier-c1 { background: #FAF5FF; border: 1px solid #E9D5FF; color: #6B21A8; }

.tl-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
  margin: 12px 0 18px 0;
}

.tl-meta-box {
  background: #FFFFFF;
  border: 1px solid var(--tl-border);
  border-radius: 10px;
  padding: 10px 14px;
}

.tl-meta-label {
  font-size: 0.72rem;
  color: #64748B;
  text-transform: uppercase;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.tl-meta-value {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--tl-navy);
  margin-top: 3px;
}

.tl-warmup-card {
  background: #FFFFFF;
  border: 1.5px solid var(--tl-border);
  border-radius: 10px;
  padding: 14px 16px;
  min-height: 85px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

.tl-warmup-num {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--tl-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.tl-warmup-text {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1E293B;
  margin-top: 4px;
  line-height: 1.4;
}

.tl-host-cue {
  background: #FFFFFF;
  border: 1px solid var(--tl-border);
  border-left: 4px solid var(--tl-primary);
  border-radius: 8px;
  padding: 12px 16px;
  margin: 12px 0;
}

.tl-cue-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--tl-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.tl-cue-text {
  font-size: 0.95rem;
  color: #1E293B;
  margin-top: 4px;
  line-height: 1.5;
}

.tl-stage-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #FFFFFF;
  border: 1px solid var(--tl-border);
  border-radius: 8px;
  margin-bottom: 6px;
}

.tl-stage-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background: var(--tl-primary-light);
  color: var(--tl-primary);
  border-radius: 50%;
  font-size: 0.8rem;
  font-weight: 700;
}

.tl-stage-title {
  font-size: 0.92rem;
  font-weight: 600;
  color: #1E293B;
}

.tl-vocab-item {
  background: #FFFFFF;
  border: 1px solid var(--tl-border);
  border-radius: 10px;
  padding: 10px 14px;
  margin-bottom: 8px;
  border-left: 4px solid var(--tl-primary);
}

.tl-vocab-expr {
  font-weight: 700;
  color: #0F172A;
  font-size: 0.98rem;
}

.tl-vocab-turkish {
  display: inline-block;
  background: #FEF3C7;
  color: #92400E;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 0.82rem;
  font-weight: 600;
  margin-left: 8px;
}

.tl-vocab-example {
  font-style: italic;
  color: #475569;
  font-size: 0.9rem;
  margin-top: 4px;
}

.tl-grammar-box {
  background: #FFFFFF;
  border: 1px solid var(--tl-border);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 14px;
}

.tl-grammar-title {
  font-size: 1rem;
  font-weight: 700;
  color: #0F172A;
}

.tl-grammar-desc {
  font-size: 0.92rem;
  color: #475569;
  margin-top: 4px;
}

.tl-grammar-pattern {
  background: #EEF2FF;
  color: #3730A3;
  font-family: monospace;
  padding: 6px 12px;
  border-radius: 6px;
  margin: 8px 0;
  font-size: 0.9rem;
}

.tl-grammar-examples-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #64748B;
  margin-top: 8px;
}

.tl-grammar-examples-list {
  margin: 4px 0 0 16px;
  font-size: 0.9rem;
  color: #334155;
}
</style>''',unsafe_allow_html=True)

if 'defaults' not in st.session_state:
    try:
        st.session_state['defaults']=load_settings()
    except ValueError as exc:
        st.session_state['defaults']=UserSettings()
        st.session_state['settings_warning']=str(exc)
defaults=st.session_state['defaults']
models = available_models()
generation_model = defaults.model if defaults.model in models else next(iter(models), None)

st.title('⚡ TalkLine Studio')
st.caption('Your personal session workspace')

status_bar = st.empty()
if st.session_state.get('settings_warning'):
    st.warning(st.session_state['settings_warning'])
if st.session_state.get('run_restore_warning'):
    st.warning(st.session_state['run_restore_warning'])
if st.session_state.get('run_restored'):
    st.caption('Reopened your last saved work.')

topic=st.text_input('Your topic',max_chars=110,key='topic_input',
                    placeholder='For example, negotiating a pay raise',
                    on_change=start_new_topic, args=(st.session_state.get('topic_input', ''),))
concept_status = st.empty()
with st.expander('Vocabulary and grammar reference sources'):
    st.caption('Online editorial references. Automatic importing is not yet implemented.')
    st.markdown('[Oxford 3000/5000: vocabulary through C1](https://www.oxfordlearnersdictionaries.com/wordlists/oxford3000-5000)')
    st.markdown('[Cambridge English–Turkish: meanings, with stated A1–B2 coverage](https://dictionary.cambridge.org/dictionary/english-turkish/)')
    st.markdown('[British Council A1–A2 grammar](https://learnenglish.britishcouncil.org/free-resources/grammar/a1-a2)')
    st.markdown('[British Council B1–B2 grammar](https://learnenglish.britishcouncil.org/free-resources/grammar/b1-b2)')
    st.markdown('[British Council C1 grammar](https://learnenglish.britishcouncil.org/free-resources/grammar/c1)')
with st.sidebar:
    st.header('Settings')
    selection=st.selectbox('Session concept', ['auto']+list(LABELS),
                           format_func=lambda key:'Automatic from topic' if key=='auto' else (
                               f"{LABELS[key]} (Full 25-slide session)" if key in FULL_WORKFLOWS else f"{LABELS[key]} (5-slide preview)"
                           ),key='concept_input')
    auto_review=False
    with st.expander('Event information and saved defaults (optional)'):
        st.session_state.setdefault('venue_input', defaults.event.venue)
        st.session_state.setdefault('date_input', defaults.event.date)
        st.session_state.setdefault('time_input', defaults.event.time)
        venue=st.text_input('Location',max_chars=60,placeholder='Optional — no venue assumed',key='venue_input')
        event_date=st.text_input('Date',max_chars=60,placeholder='Optional — no date assumed',key='date_input')
        event_time=st.text_input('Time',max_chars=60,placeholder='Optional — no time assumed',key='time_input')
        st.caption('Only details you enter are used. Save explicitly to reuse them next time; check the saved date before each event.')
        if st.button('Save event defaults',key='save_defaults'):
            try:
                settings=UserSettings(EventDetails(venue,event_date,event_time,defaults.event.feedback_url),defaults.model)
                save_settings(settings)
                st.session_state['defaults']=settings
                st.session_state.pop('settings_warning',None)
                st.success('Defaults saved locally in user_data/settings.json.')
            except (ValueError,OSError) as exc:
                st.error(f'Could not save defaults: {exc}')

    if not generation_model:
        st.warning('Start Ollama and make sure a local model is installed. To install the default model, run `ollama pull qwen3:8b`.')
    concept = selection
    if selection == 'auto':
        try:
            concept = automatic_concept(topic.strip(), generation_model)
        except (RuntimeError, ValueError, OSError) as exc:
            concept = None
            concept_status.warning(f'Could not choose a concept. Retry or choose one in Settings. {exc}')
            st.button('Retry concept selection', key='retry_concept')
    if concept in LABELS and concept not in FULL_WORKFLOWS:
        auto_review=st.checkbox('Review language levels and game logic automatically (local AI)',value=True)

model_pill = (f'<span class="tl-pill tl-pill-green">● Local AI: {escape(generation_model)}</span>'
              if generation_model else '<span class="tl-pill tl-pill-red">● Local model unavailable</span>')
concept_label = LABELS.get(concept, 'Automatic from topic')
if concept in FULL_WORKFLOWS:
    concept_label += ' · full 25-slide session'
elif concept in LABELS:
    concept_label += ' · five-slide prototype'
status_bar.markdown(f'''
<div class="tl-status-bar">
    {model_pill}
    <span class="tl-pill tl-pill-indigo">🎯 {escape(concept_label)}</span>
    <span class="tl-pill tl-pill-blue">🔒 Local &amp; Private</span>
</div>
''', unsafe_allow_html=True)

with st.expander('Topic Toolkit · vocabulary, phrases and mini grammar'):
    st.download_button('Openable sample Toolkit · Office Boundaries (HTML)',
                       toolkit_html(sample_toolkit()), file_name='TalkLine_Toolkit_Sample.html', mime='text/html')
    st.caption('Local AI creates A1/A2, B1 and B2/C1 material with Turkish meanings and English examples. Grammar exports on separate pages. Preview before teaching; level and relevance need human review.')
    if st.button('Generate Toolkit with local AI', key='generate_toolkit', disabled=not topic.strip() or not generation_model):
        try:
            with st.spinner('Creating Toolkit for three levels...'):
                toolkit = generate_toolkit(topic, generation_model)
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
        else:
            set_toolkit(st.session_state, toolkit)
            save_current_run()
    toolkit = st.session_state.get('toolkit')
    if not toolkit or toolkit['topic'] != topic.strip():
        toolkit = st.session_state.get('event_toolkit')
    if toolkit and toolkit['topic'] == topic.strip():
        flagged = [item for item in toolkit.get('vocabulary_profile', []) if item['status'] != 'level_match']
        if flagged:
            st.warning('Check vocabulary levels: ' + ', '.join(item['expression'] for item in flagged))
        with st.expander('Source details'):
            st.write(toolkit.get('profile_attribution', 'No automated profile lookup recorded.'))
            st.json(toolkit.get('vocabulary_profile', []), expanded=False)
        if toolkit.get('review_error'):
            st.warning('Toolkit language review failed: ' + toolkit['review_error'])
        if toolkit.get('review'):
            st.write(toolkit['review']['summary'])
            for issue in toolkit['review']['issues']:
                message = f"{LEVEL_LABELS[issue['level']]}: {issue['message']}"
                if issue['severity'] == 'error':
                    st.error(message)
                else:
                    st.warning(message)
            st.caption('Local AI review is advisory. Check Turkish meanings and teaching suitability before use.')
        for level, material in toolkit['levels'].items():
            st.subheader(LEVEL_LABELS[level] + ' / Vocabulary, phrases and idioms')
            for kind in ('vocabulary', 'phrases', 'idioms'):
                if material.get(kind):
                    st.markdown(f"**{kind.title()}**")
                    for entry in material[kind]:
                        st.markdown(f'''
                        <div class="tl-vocab-item">
                            <span class="tl-vocab-expr">{escape(entry['expression'])}</span>
                            <span class="tl-vocab-turkish">{escape(entry['turkish'])}</span>
                            <div class="tl-vocab-example">"{escape(entry['example'])}"</div>
                        </div>
                        ''', unsafe_allow_html=True)
            grammar = material['mini_grammar']
            st.subheader(LEVEL_LABELS[level] + ' / Grammar')
            st.markdown(f'''
            <div class="tl-grammar-box">
                <div class="tl-grammar-title">Mini grammar: {escape(grammar['title'])}</div>
                <div class="tl-grammar-desc">{escape(grammar['explanation'])}</div>
                <div class="tl-grammar-pattern"><strong>Pattern:</strong> {escape(grammar['pattern'])}</div>
                <div class="tl-grammar-examples-title">Examples:</div>
                <ul class="tl-grammar-examples-list">
                    {''.join(f'<li>{escape(ex)}</li>' for ex in grammar['examples'])}
                </ul>
            </div>
            ''', unsafe_allow_html=True)
        st.download_button('Download Toolkit JSON', json.dumps(toolkit, ensure_ascii=False, indent=2),
                           file_name='TalkLine_Toolkit.json', mime='application/json')
        st.download_button('Download readable Toolkit HTML', toolkit_html(toolkit),
                           file_name='TalkLine_Toolkit.html', mime='text/html')
        if st.button('Build editable Toolkit PowerPoint', key='build_toolkit_pptx'):
            try:
                st.session_state['toolkit_deck'] = build_toolkit_pptx(toolkit)
                st.session_state['toolkit_deck_version'] = content_fingerprint(toolkit)
            except (ValueError, OSError) as exc:
                st.error(f'Toolkit export failed: {exc}')
        version = content_fingerprint(toolkit)
        if st.session_state.get('toolkit_deck_version') == version:
            st.download_button('Download Toolkit PowerPoint', st.session_state['toolkit_deck'],
                               file_name='TalkLine_Toolkit.pptx', mime='application/vnd.openxmlformats-officedocument.presentationml.presentation')
        st.caption('The standalone Toolkit PowerPoint uses the Business English template.')

selected_workflow = FULL_WORKFLOWS.get(concept)
full_workflow_selected = selected_workflow is not None
generate_label = f'Generate {LABELS[concept]} session' if full_workflow_selected else 'Generate prototype'
if concept is None:
    generate_label = 'Generate session'
pending = None
start_over = False
if full_workflow_selected and generation_model and topic.strip():
    try:
        pending = load_session_progress(concept, topic.strip(), generation_model)
    except (ValueError, OSError) as exc:
        st.warning(f'An unfinished session could not be read. A new run can still start. {exc}')
    if pending is not None:
        generate_label = f'Resume {LABELS[concept]} generation'
        start_over = st.checkbox('Start over with new content', key='restart_full_generation')
        if start_over:
            generate_label = f'Generate new {LABELS[concept]} session'

if st.button(generate_label,key='generate',type='primary',use_container_width=True,disabled=not topic.strip() or not generation_model or not concept):
    latest_progress = {'checkpoint': None if start_over else pending}
    try:
        if full_workflow_selected:
            # Save a completed Toolkit even if a later generation request fails.
            candidates = (st.session_state.get('toolkit'), st.session_state.get('event_toolkit'))
            has_toolkit = any(material and (material.get('topic'), material.get('model')) ==
                              (topic.strip(), generation_model) for material in candidates)
            if not has_toolkit:
                with st.spinner('Creating the session Toolkit...'):
                    material = generate_toolkit(topic, generation_model)
                set_toolkit(st.session_state, material)
                save_current_run()
            generate_session = SESSION_GENERATORS[selected_workflow]
            with st.spinner('Creating the warm-up and speaking activities...'):
                progress_bar = st.progress(0, text='Preparing the local model...')

                def record_progress(completed, total, checkpoint):
                    latest_progress['checkpoint'] = checkpoint
                    try:
                        save_session_progress(concept, topic.strip(), generation_model, checkpoint,
                                              automatic=selection == 'auto')
                    except (ValueError, OSError) as exc:
                        progress_bar.progress(completed / total, text=f'Completed batches: {completed} of {total}')
                        st.warning(f'Could not save this batch for later. {exc}')
                    else:
                        progress_bar.progress(completed / total, text=f'Saved batches: {completed} of {total}')

                brief = generate_session(topic, generation_model, resume=None if start_over else pending,
                                         on_progress=record_progress)
        else:
            with st.spinner('Creating local speaking content...'):
                brief = create_with_ollama(topic, model=generation_model)
    except Exception as exc:
        st.error(f'Content generation failed. {exc}')
        if st.session_state.get('brief'):
            st.info('Your previous successful work is still available.')
    else:
        for old_key in ('review','review_warning'):
            st.session_state.pop(old_key, None)
        st.session_state['brief']=brief
        st.session_state['metadata']={'topic':topic.strip(),'venue':venue.strip(),'date':event_date.strip(),'time':event_time.strip(),'mode':LOCAL_MODE,'model':generation_model,'concept':concept}
        if selection == 'auto':
            st.session_state['metadata']['concept_selection'] = 'auto'
        if full_workflow_selected:
            st.session_state['metadata']['workflow'] = selected_workflow
        if st.session_state.get('event_toolkit', {}).get('topic') != topic.strip():
            st.session_state.pop('event_toolkit', None)
        saved_to_disk = save_current_run()
        if saved_to_disk and full_workflow_selected and generation_model:
            try:
                clear_session_progress(concept, topic.strip(), generation_model, latest_progress['checkpoint'])
            except (ValueError, OSError) as exc:
                st.warning(f'The session is saved. Its unfinished progress file could not be cleared. {exc}')
        if auto_review and not full_workflow_selected:
            try:
                with st.spinner('Content created. Reviewing language levels and game logic locally...'):
                    st.session_state['review']=review_brief(topic,brief,model=generation_model)
                if any(issue['severity']=='error' for issue in st.session_state['review']['issues']):
                    try:
                        with st.spinner('The local review found an error. Repairing one section and reviewing again...'):
                            repaired=repair_reviewed_brief(topic,brief,st.session_state['review'],generation_model)
                        st.session_state['brief']=repaired['content']
                        st.session_state['review']=repaired['review']
                        st.session_state['metadata']['repaired_section']=repaired['repaired_section']
                    except Exception as exc:
                        st.session_state['review_warning']=f'Automatic repair failed; the original content and its flagged review are retained: {exc}'
            except Exception as exc:
                st.session_state['review_warning']=f'Content is structurally valid, but the local quality review failed: {exc}'
            save_current_run()
        st.success('Content created. Review it below, then build your files.')

if st.session_state.get('brief'):
    brief=st.session_state['brief']; meta=st.session_state['metadata']
    workflow = meta.get('workflow')
    full_session = workflow in FULL_WORKFLOWS.values()
    # Older automatic drafts used "auto" for invitation style and saved a prototype.
    form_concept = selection if meta.get('concept') == 'auto' else concept
    current_inputs = {'topic': topic.strip(), 'venue': venue.strip(), 'date': event_date.strip(),
                      'time': event_time.strip(), 'concept': form_concept}
    inputs_match = all((meta.get(key) or '') == (value or '') for key, value in current_inputs.items())
    if not inputs_match:
        st.info(f"You’re viewing the previous run for “{meta['topic']}”. Generate with your new inputs or load the saved event details.")
        st.button('Load saved event details', key='load_saved_inputs',
                  on_click=set_event_widgets, args=(st.session_state,))
    session_toolkit = toolkit_for_event(draft_from_state(st.session_state))
    stages = build_session_sequence(meta, brief, include_toolkit=session_toolkit is not None)
    critical_issues=[]
    export_override=False
    st.caption('The export uses the event details shown below. Generate again to apply changes from the form.')
    st.markdown(f'''
    <div class="tl-meta-grid">
        <div class="tl-meta-box">
            <div class="tl-meta-label">Location</div>
            <div class="tl-meta-value">📍 {escape(meta.get('venue') or 'Not specified')}</div>
        </div>
        <div class="tl-meta-box">
            <div class="tl-meta-label">Date</div>
            <div class="tl-meta-value">📅 {escape(meta.get('date') or 'Not specified')}</div>
        </div>
        <div class="tl-meta-box">
            <div class="tl-meta-label">Time</div>
            <div class="tl-meta-value">⏰ {escape(meta.get('time') or 'Not specified')}</div>
        </div>
        <div class="tl-meta-box">
            <div class="tl-meta-label">Concept</div>
            <div class="tl-meta-value">🎯 {escape(LABELS.get(meta['concept'], 'Automatic'))}</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    st.subheader('Generated content')
    st.write('**Topic:**',meta['topic'])
    st.write('**Subtitle:**',brief['subtitle'])
    st.subheader('Warm-up')
    w_cols = st.columns(len(brief['warmup']))
    for i, (col, q) in enumerate(zip(w_cols, brief['warmup'], strict=True), 1):
        col.markdown(f'''
        <div class="tl-warmup-card">
            <div class="tl-warmup-num">Question {i}</div>
            <div class="tl-warmup-text">{escape(q)}</div>
        </div>
        ''', unsafe_allow_html=True)
    if full_session and 'round1' in brief:
        with st.expander('Round 1 discussion cards'):
            for number, card in enumerate(brief['round1'], 1):
                st.subheader(f"{number}. {card['title']}")
                scene, questions = discussion_preview(card)
                scene_html = f'<div class="tl-card-scene"><strong>Scene:</strong> {escape(scene)}</div>' if scene else ''
                st.markdown(f'''
                <div class="tl-round-card">
                    {scene_html}
                    <div class="tl-tier-row">
                        <span class="tl-tier-badge tl-tier-a2">A2 Personal</span>
                        <span>{escape(questions['a2'])}</span>
                    </div>
                    <div class="tl-tier-row">
                        <span class="tl-tier-badge tl-tier-b2">B2 Social</span>
                        <span>{escape(questions['b2'])}</span>
                    </div>
                    <div class="tl-tier-row">
                        <span class="tl-tier-badge tl-tier-c1">C1 Dilemma</span>
                        <span>{escape(questions['c1'])}</span>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
    elif 'round1' in brief:
        st.write('**Round 1 sample:**')
        st.json(brief['round1'],expanded=False)
    if full_session:
        st.markdown(f'''
        <div class="tl-host-cue">
            <div class="tl-cue-label">🎙️ Host Opening Script</div>
            <div class="tl-cue-text">{escape(brief['opening'])}</div>
        </div>
        ''', unsafe_allow_html=True)
        games = brief['games'] if workflow == FULL_GAME_NIGHT else [brief['game']]
        for game in games:
            with st.expander(f"Preview {game['title']}"):
                st.caption(f"{len(game['elementary'])} Elementary and {len(game['advanced'])} Advanced cards")
                st.json(game, expanded=False)
        st.markdown(f'''
        <div class="tl-host-cue">
            <div class="tl-cue-label">🎯 Host Wrap-Up Reflection</div>
            <div class="tl-cue-text">{escape(brief['closing'])}</div>
        </div>
        ''', unsafe_allow_html=True)
    else:
        st.write('**Game sample:**')
        st.json(brief['game_cards'],expanded=False)
    with st.expander('Meeting sequence'):
        for number, stage in enumerate(stages, 1):
            st.markdown(f'''
            <div class="tl-stage-step">
                <span class="tl-stage-num">{number}</span>
                <span class="tl-stage-title">{escape(stage['title'])}</span>
            </div>
            ''', unsafe_allow_html=True)
        if session_toolkit is None:
            st.caption('Generate a Toolkit for this topic to include vocabulary and mini grammar.')
    if meta['mode'] == DEMO_MODE:
        st.caption('This saved session contains example material.')
    elif not full_session:
        st.caption('Structure validated. Meaning, language level and causal logic still need review.')
        if st.session_state.get('review_warning'):
            st.warning(st.session_state['review_warning'])
        if st.button('Review content with local AI',key='review_content'):
            try:
                with st.spinner('Reviewing language levels and game logic locally...'):
                    st.session_state['review']=review_brief(meta['topic'],brief,model=meta['model'])
                    st.session_state.pop('review_warning',None)
                    save_current_run()
            except Exception as exc:
                st.error(f'Local review failed: {exc}')
        report=st.session_state.get('review')
        if report:
            st.write('**Local AI review (advisory):**',report['summary'])
            genuine_issues = []
            for issue in report['issues']:
                msg = issue.get('message', '').strip().lower()
                if any(p in msg for p in [
                    'no issue', 'no issues', 'no problem', 'no errors',
                    'none detected', 'not detected', 'no concerns'
                ]) and not any(p in msg for p in ['instead of', 'however', 'but', 'except', 'unrealistic', 'inconsistent']):
                    continue
                genuine_issues.append(issue)
            if not genuine_issues:
                st.success('No issues flagged by local AI review.')
            else:
                for issue in genuine_issues:
                    st.warning(f"{issue['section']} · {issue['severity']}: {issue['message']}")
            st.caption('This review is a model opinion, not proof of correct CEFR or game logic.')
            critical_issues=[issue for issue in genuine_issues if issue['severity']=='error']
            if critical_issues:
                st.error('The local review still flags content errors. Regenerate the affected section or review this prototype yourself before exporting.')
                revision=hashlib.sha256(json.dumps([meta,brief,report],sort_keys=True).encode()).hexdigest()[:12]
                export_override=st.checkbox('I reviewed the flagged content and want to export this prototype.',key=f'override_{revision}')
        with st.expander('Regenerate one section'):
            section=st.selectbox('Section',['subtitle','tagline','warmup','round1','game_cards'])
            feedback=st.text_area('What should improve? (optional)',max_chars=1500)
            if st.button('Regenerate selected section locally',key='regenerate'):
                try:
                    with st.spinner('Rewriting and validating just this section...'):
                        updated=regenerate_section(meta['topic'],brief,section,feedback,meta['model'])
                    st.session_state['brief']=updated
                    for key in ('review','review_warning'):
                        st.session_state.pop(key,None)
                    save_current_run()
                    st.rerun()
                except Exception as exc:
                    st.error(f'Section regeneration failed; previous valid content is retained: {exc}')
    if full_session:
        updated = edit_session(brief, SESSION_VALIDATORS[workflow])
        if updated is not None:
            st.session_state['brief'] = updated
            save_current_run()
            st.rerun()
    revision = export_revision(draft_from_state(st.session_state))
    regenerate_full_section = SECTION_REGENERATORS.get(workflow)
    if regenerate_full_section and meta['model']:
        with st.expander('Regenerate one session section'):
            full_section = st.selectbox('Section', ['opening', 'warmup', 'round1', 'game', 'closing'],
                                        key='full_section')
            full_feedback = st.text_area('What should improve?', max_chars=1500, key='full_feedback')
            if st.button('Regenerate session section', key='regenerate_full'):
                try:
                    with st.spinner('Rewriting and validating the selected section...'):
                        revised = regenerate_full_section(
                            meta['topic'], brief, full_section, meta['model'], full_feedback)
                except (ValueError, RuntimeError) as exc:
                    st.error(f'Section regeneration failed. {exc}')
                else:
                    st.session_state['brief'] = revised
                    save_current_run()
                    st.rerun()

    if not inputs_match:
        st.warning('The event details above (topic, concept, date, or location) do not match this saved session. Click "Load saved event details" above to sync them, or click Generate to create a new session.')
    elif full_session and session_toolkit is None:
        st.warning('A Topic Toolkit is required to build the full session presentation. Please click "Generate Toolkit with local AI" in the Topic Toolkit section above.')
    elif bool(critical_issues) and not export_override:
        st.warning('The local quality review flagged critical issues above. Check "I reviewed the flagged content and want to export this prototype" above to proceed with export.')

    if st.button('Build session files' if full_session else 'Build prototype files',
                 key='build',type='primary',use_container_width=True,
                 disabled=not inputs_match or (full_session and session_toolkit is None)
                 or (bool(critical_issues) and not export_override)):
        try:
            with st.spinner('Building the host guide, game and invitation...'):
                export = build_session_export(
                    meta, brief, session_toolkit, review=st.session_state.get('review'),
                    review_warning=st.session_state.get('review_warning'),
                    reviewed_flagged_content=export_override,
                )
                st.session_state['package'] = export.archive
                st.session_state['invitation_size'] = export.invitation_size
                st.session_state['package_revision'] = revision
                save_current_run()
            st.success('Generated locally — no paid APIs used.')
        except Exception as exc:
            st.error(f'Export failed: {exc}')
    if inputs_match and st.session_state.get('package') and st.session_state.get('package_revision') != revision:
        st.info('The saved files are for an earlier version. Build the files again to download this version.')
    elif inputs_match and st.session_state.get('package'):
        with zipfile.ZipFile(BytesIO(st.session_state['package'])) as archive:
            filename = presentation_filename(meta)
            st.markdown('''
            <div style="background: #F0FDF4; border: 1.5px solid #86EFAC; border-radius: 12px; padding: 14px 18px; margin: 16px 0 14px 0;">
                <div style="font-size: 1rem; font-weight: 700; color: #166534;">🎉 Your session files are ready!</div>
                <div style="font-size: 0.88rem; color: #15803D; margin-top: 2px;">Use the extracted ZIP to play games from the presentation. The Rate Us form opens online.</div>
            </div>
            ''', unsafe_allow_html=True)
            presentation, invitation = st.columns(2)
            presentation.download_button(
                'Download PowerPoint', archive.read(filename), file_name=filename,
                mime='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                use_container_width=True,
            )
            invitation.download_button(
                'Download invitation GIF', archive.read('TalkLine_Invitation.gif'),
                file_name='TalkLine_Invitation.gif', mime='image/gif', use_container_width=True,
            )
            st.image(archive.read('TalkLine_Invitation.png'), caption='Invitation preview')
        with st.expander('Local game files'):
            st.write('Extract the ZIP and open the PowerPoint inside it to use its game links.')
            st.download_button('Download session ZIP' if full_session else 'Download complete prototype ZIP',
                               st.session_state['package'],
                               file_name='TalkLine_Session.zip' if full_session else 'TalkLine_Studio_Prototype.zip',
                               mime='application/zip', use_container_width=True)

if st.session_state.get('run_save_warning'):
    st.warning(st.session_state['run_save_warning'])
st.divider()
st.caption('Everything runs locally. The only internet download required is installing free packages and the AI model once. No ChatGPT/Claude subscription or API key required.')
