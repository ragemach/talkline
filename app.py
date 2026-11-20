"""TalkLine Studio's local session workspace."""
from __future__ import annotations
import json
import hashlib
import zipfile
from io import BytesIO
import streamlit as st
from src.ai_content import available_models, create_with_ollama, demo_brief, review_brief, regenerate_section, repair_reviewed_brief
from src.business_content import generate_business, regenerate_business_section, validate_business
from src.game_night_content import generate_game_night, validate_game_night
from src.invitation_content import LABELS
from src.settings import EventDetails, UserSettings, load_settings, save_settings
from src.toolkit import generate_toolkit, LEVEL_LABELS
from src.toolkit_export import toolkit_html
from src.toolkit_library import sample_toolkit
from src.toolkit_pptx import build_toolkit_pptx
from src.checkpoints import (
    clear_session_progress, content_fingerprint, load_session_progress, save_session_progress,
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
from src.spontaneous_demo_toolkit import demo_spontaneous_toolkit
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
    if metadata := saved.draft.get('metadata'):
        st.session_state['engine_input'] = metadata['mode']
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


st.set_page_config(page_title='TalkLine Studio',page_icon='⚡',layout='centered')
restore_run_once()
st.markdown('''<style>
html {font-size:18px}
[data-testid="stCaptionContainer"] {color:#45546B}
button, input, textarea {font-size:1rem !important}
</style>''',unsafe_allow_html=True)

st.title('⚡ TalkLine Studio')
st.caption('Your personal session workspace')
st.info('Choose Spontaneous Talk, Business English, or Game Night for a full session.')

if 'defaults' not in st.session_state:
    try:
        st.session_state['defaults']=load_settings()
    except ValueError as exc:
        st.session_state['defaults']=UserSettings()
        st.session_state['settings_warning']=str(exc)
defaults=st.session_state['defaults']
if st.session_state.get('settings_warning'):
    st.warning(st.session_state['settings_warning'])
if st.session_state.get('run_restore_warning'):
    st.warning(st.session_state['run_restore_warning'])
if st.session_state.get('run_restored'):
    st.caption('Reopened your last saved work.')

st.session_state.setdefault('topic_input', 'Reality Has a Glitch!')
topic=st.text_input('Your topic',max_chars=110,key='topic_input')
with st.expander('Vocabulary and grammar reference sources'):
    st.caption('Online editorial references. Automatic importing is not yet implemented.')
    st.markdown('[Oxford 3000/5000: vocabulary through C1](https://www.oxfordlearnersdictionaries.com/wordlists/oxford3000-5000)')
    st.markdown('[Cambridge English–Turkish: meanings, with stated A1–B2 coverage](https://dictionary.cambridge.org/dictionary/english-turkish/)')
    st.markdown('[British Council A1–A2 grammar](https://learnenglish.britishcouncil.org/free-resources/grammar/a1-a2)')
    st.markdown('[British Council B1–B2 grammar](https://learnenglish.britishcouncil.org/free-resources/grammar/b1-b2)')
    st.markdown('[British Council C1 grammar](https://learnenglish.britishcouncil.org/free-resources/grammar/c1)')
with st.sidebar:
    st.header('Settings')
    mode=st.radio('Content engine',options=[DEMO_MODE, LOCAL_MODE],horizontal=True,key='engine_input')
    concept=st.selectbox('Event concept (optional)', ['auto']+list(LABELS),
                         format_func=lambda key:'Choose from the topic automatically' if key=='auto' else LABELS[key],key='concept_input')
    selected_model=defaults.model
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

    if mode.startswith('Local'):
        models=available_models()
        if models:
            preferred_model = st.session_state.get('metadata', {}).get('model') or defaults.model
            selected_model=st.selectbox('Downloaded local model',models,
                                       index=models.index(preferred_model) if preferred_model in models else 0)
            st.success(f'Local model ready: {selected_model}')
            if st.button('Save selected model',key='save_model'):
                try:
                    settings=UserSettings(EventDetails(venue,event_date,event_time,defaults.event.feedback_url),selected_model)
                    save_settings(settings)
                    st.session_state['defaults']=settings
                    st.success('Local model preference saved.')
                except (ValueError,OSError) as exc:
                    st.error(f'Could not save model preference: {exc}')
        else:
            st.warning('Ollama or qwen3:8b is not ready. Install Ollama and run: `ollama pull qwen3:8b`')
        st.caption('Local generation may take several minutes on CPU. No cloud account is used.')
        if concept not in FULL_WORKFLOWS:
            auto_review=st.checkbox('Review language levels and game logic automatically (local AI)',value=True)

with st.expander('Topic Toolkit · vocabulary, phrases and mini grammar'):
    st.download_button('Openable sample Toolkit · Office Boundaries (HTML)',
                       toolkit_html(sample_toolkit()), file_name='TalkLine_Toolkit_Sample.html', mime='text/html')
    st.caption('Local AI creates A1/A2, B1 and B2/C1 material with Turkish meanings and English examples. Grammar exports on separate pages. Preview before teaching; level and relevance need human review.')
    if st.button('Generate Toolkit with local AI', key='generate_toolkit', disabled=not topic.strip() or not mode.startswith('Local') or not models):
        try:
            with st.spinner('Creating Toolkit for three levels...'):
                toolkit = generate_toolkit(topic, selected_model)
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
                for entry in material[kind]:
                    st.write(f"{kind.title()}: {entry['expression']} — {entry['turkish']}")
                    st.write(entry['example'])
            grammar = material['mini_grammar']
            st.subheader(LEVEL_LABELS[level] + ' / Grammar')
            st.write(f"Mini grammar: {grammar['title']}")
            st.write(grammar['explanation'])
            st.write(grammar['pattern'])
            for example in grammar['examples']:
                st.write(example)
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
        st.caption('Toolkit PowerPoint uses your Business English template. The complete session presentation is still in development.')

selected_workflow = FULL_WORKFLOWS.get(concept)
full_workflow_selected = selected_workflow is not None
generate_label = f'Generate {LABELS[concept]} session' if full_workflow_selected else 'Generate prototype'
generation_model = selected_model if mode == LOCAL_MODE else None
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

if st.button(generate_label,key='generate',type='primary',use_container_width=True,disabled=not topic.strip() or (mode.startswith('Local') and not models)):
    latest_progress = {'checkpoint': None if start_over else pending}
    try:
        if full_workflow_selected:
            # Save a completed Toolkit even if a later generation request fails.
            has_toolkit = any((st.session_state.get(key) or {}).get('topic') == topic.strip()
                              for key in ('toolkit', 'event_toolkit'))
            if not has_toolkit:
                with st.spinner('Creating the session Toolkit...'):
                    if generation_model:
                        material = generate_toolkit(topic, generation_model)
                    elif selected_workflow == FULL_GAME_NIGHT:
                        from src.game_night_demo_toolkit import demo_game_night_toolkit
                        material = demo_game_night_toolkit(topic)
                    elif selected_workflow == FULL_BUSINESS:
                        material = sample_toolkit()
                        material['topic'] = topic.strip()
                    else:
                        material = demo_spontaneous_toolkit(topic)
                set_toolkit(st.session_state, material)
                save_current_run()
            generate_session = SESSION_GENERATORS[selected_workflow]
            with st.spinner('Creating the warm-up and speaking activities...'):
                if generation_model is None:
                    brief = generate_session(topic)
                else:
                    progress_bar = st.progress(0, text='Preparing the local model...')

                    def record_progress(completed, total, checkpoint):
                        latest_progress['checkpoint'] = checkpoint
                        try:
                            save_session_progress(concept, topic.strip(), generation_model, checkpoint)
                        except (ValueError, OSError) as exc:
                            progress_bar.progress(completed / total, text=f'Completed batches: {completed} of {total}')
                            st.warning(f'Could not save this batch for later. {exc}')
                        else:
                            progress_bar.progress(completed / total, text=f'Saved batches: {completed} of {total}')

                    brief = generate_session(topic, generation_model, resume=None if start_over else pending,
                                             on_progress=record_progress)
        else:
            with st.spinner('Creating local speaking content...'):
                brief = (create_with_ollama(topic, model=generation_model) if generation_model
                         else demo_brief(topic))
    except Exception as exc:
        st.error(f'Content generation failed. {exc}')
        if st.session_state.get('brief'):
            st.info('Your previous successful work is still available.')
    else:
        for old_key in ('review','review_warning'):
            st.session_state.pop(old_key, None)
        st.session_state['brief']=brief
        st.session_state['metadata']={'topic':topic.strip(),'venue':venue.strip(),'date':event_date.strip(),'time':event_time.strip(),'mode':mode,'model':selected_model if mode.startswith('Local') else None,'concept':concept}
        if full_workflow_selected:
            st.session_state['metadata']['workflow'] = selected_workflow
        if st.session_state.get('event_toolkit', {}).get('topic') != topic.strip():
            st.session_state.pop('event_toolkit', None)
        if mode.startswith('Demo') and topic.strip().casefold() == 'office boundaries':
            if toolkit_for_event(draft_from_state(st.session_state)) is None:
                editorial_toolkit = sample_toolkit()
                editorial_toolkit['topic'] = topic.strip()
                set_toolkit(st.session_state, editorial_toolkit)
        saved_to_disk = save_current_run()
        if saved_to_disk and full_workflow_selected and generation_model:
            try:
                clear_session_progress(concept, topic.strip(), generation_model, latest_progress['checkpoint'])
            except (ValueError, OSError) as exc:
                st.warning(f'The session is saved. Its unfinished progress file could not be cleared. {exc}')
        if auto_review and not full_workflow_selected:
            try:
                with st.spinner('Content created. Reviewing language levels and game logic locally...'):
                    st.session_state['review']=review_brief(topic,brief,model=selected_model)
                if any(issue['severity']=='error' for issue in st.session_state['review']['issues']):
                    try:
                        with st.spinner('The local review found an error. Repairing one section and reviewing again...'):
                            repaired=repair_reviewed_brief(topic,brief,st.session_state['review'],selected_model)
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
    current_inputs = {'topic': topic.strip(), 'venue': venue.strip(), 'date': event_date.strip(),
                      'time': event_time.strip(), 'concept': concept}
    inputs_match = all(meta.get(key) == value for key, value in current_inputs.items())
    if not inputs_match:
        st.info(f"You’re viewing the previous run for “{meta['topic']}”. Generate with your new inputs or load the saved event details.")
        st.button('Load saved event details', key='load_saved_inputs',
                  on_click=set_event_widgets, args=(st.session_state,))
    session_toolkit = toolkit_for_event(draft_from_state(st.session_state))
    stages = build_session_sequence(meta, brief, include_toolkit=session_toolkit is not None)
    critical_issues=[]
    export_override=False
    st.caption('The export uses the event details shown below. Generate again to apply changes from the form.')
    st.write('**Event details:**', {k: meta[k] or 'Not supplied' for k in ('venue','date','time')})
    st.subheader('Generated content')
    st.write('**Topic:**',meta['topic'])
    st.write('**Subtitle:**',brief['subtitle'])
    st.write('**Warm-up:**',brief['warmup'])
    if 'round1' in brief:
        st.write('**Round 1 discussion:**' if full_session else '**Round 1 sample:**')
        st.json(brief['round1'],expanded=False)
    if full_session:
        st.write('**Opening**', brief['opening'])
        games = brief['games'] if workflow == FULL_GAME_NIGHT else [brief['game']]
        for game in games:
            with st.expander(f"Preview {game['title']}"):
                st.caption(f"{len(game['elementary'])} Elementary and {len(game['advanced'])} Advanced cards")
                st.json(game, expanded=False)
        st.write('**Wrap-up**', brief['closing'])
    else:
        st.write('**Game sample:**')
        st.json(brief['game_cards'],expanded=False)
    with st.expander('Meeting sequence'):
        for number, stage in enumerate(stages, 1):
            st.write(f"{number}. {stage['title']}")
        if session_toolkit is None:
            st.caption('Generate a Toolkit for this topic to include vocabulary and mini grammar. To see those sections in Demo, use Office Boundaries.')
    if meta['mode'].startswith('Demo'):
        st.caption('Demo mode uses reusable example content. For topic-specific creative writing, choose Local Ollama AI.')
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
            for issue in report['issues']:
                st.warning(f"{issue['section']} · {issue['severity']}: {issue['message']}")
            st.caption('This review is a model opinion, not proof of correct CEFR or game logic.')
            critical_issues=[issue for issue in report['issues'] if issue['severity']=='error']
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
            st.image(archive.read('TalkLine_Invitation.png'),caption='Original-template invitation preview · English')
            st.download_button('Download session ZIP' if full_session else 'Download complete prototype ZIP',
                               st.session_state['package'],
                               file_name='TalkLine_Session.zip' if full_session else 'TalkLine_Studio_Prototype.zip',
                               mime='application/zip',use_container_width=True)
            st.caption('Extract the ZIP and open TalkLine_Host_Guide.html to follow the meeting sequence.')
            filenames = game_filenames(meta)
            labels = ('Download Taboo', 'Download Problem Solver') if workflow == FULL_GAME_NIGHT else ('Download offline speaking game',)
            for label, filename in zip(labels, filenames, strict=True):
                st.download_button(label, archive.read(filename), file_name=filename, mime='text/html')
            left,right=st.columns(2)
            with left:
                st.download_button('Invitation GIF · original proportions',archive.read('TalkLine_Invitation.gif'),
                        file_name='TalkLine_Invitation.gif',mime='image/gif',use_container_width=True)
            with right:
                filename = presentation_filename(meta)
                st.download_button('Session PowerPoint' if full_session else 'Mini PowerPoint', archive.read(filename),
                        file_name=filename if full_session else 'TalkLine_Mini_Deck.pptx',mime='application/vnd.openxmlformats-officedocument.presentationml.presentation',use_container_width=True)
            st.download_button('Editable invitation PowerPoint',archive.read('TalkLine_Invitation.pptx'),
                               file_name='TalkLine_Invitation.pptx',mime='application/vnd.openxmlformats-officedocument.presentationml.presentation')
        width,height=st.session_state['invitation_size']
        st.caption(f'GIF: {width} × {height}, 8 seconds, looping, subtle fade and readable hold. Original sample proportions preserved. GIF has a 256-colour limit; a PNG and editable invitation are included in the ZIP.')

if st.session_state.get('run_save_warning'):
    st.warning(st.session_state['run_save_warning'])
st.divider()
st.caption('Everything runs locally. The only internet download required is installing free packages and the AI model once. No ChatGPT/Claude subscription or API key required.')
