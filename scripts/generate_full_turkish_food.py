"""Generate a complete 25-slide Spontaneous Talk session for 'turkish food' and save as current run."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checkpoints import load_session_progress, save_session_progress
from src.run_state import LOCAL_MODE, export_revision
from src.run_store import save_run
from src.session_export import build_session_export
from src.session_sequence import FULL_SPONTANEOUS
from src.spontaneous_content import generate_spontaneous
from src.toolkit import generate_toolkit


def main():
    topic = "turkish food"
    model = "qwen3:8b"
    concept = "spontaneous"
    toolkit_cache = Path(__file__).resolve().parents[1] / 'user_data' / 'turkish_food_toolkit.json'

    if toolkit_cache.exists():
        print(f"1. Loading cached Topic Toolkit for {topic!r}...")
        toolkit = json.loads(toolkit_cache.read_text(encoding='utf-8'))
    else:
        print(f"1. Generating Topic Toolkit for {topic!r} with {model}...")
        toolkit = generate_toolkit(topic, model)
        toolkit_cache.write_text(json.dumps(toolkit, ensure_ascii=False, indent=2), encoding='utf-8')
    print("   Toolkit ready!")
    print(f"   Vocabulary count: A1/A2: {len(toolkit['levels']['a2']['vocabulary'])}, B1: {len(toolkit['levels']['b1']['vocabulary'])}, B2/C1: {len(toolkit['levels']['b2_c1']['vocabulary'])}")

    print(f"2. Generating Spontaneous Talk session content (10 cards, cues, Patch Notes game)...")
    pending = load_session_progress(concept, topic, model)

    def on_progress(completed, total, checkpoint):
        print(f"   Progress: {completed}/{total} batches completed...")
        save_session_progress(concept, topic, model, checkpoint, automatic=True)

    brief = generate_spontaneous(topic, model, resume=pending, on_progress=on_progress)
    print("   Spontaneous content generated successfully!")
    print(f"   Cards count: {len(brief['round1'])}")

    metadata = {
        'topic': topic,
        'venue': '',
        'date': '',
        'time': '20:00',
        'mode': LOCAL_MODE,
        'model': model,
        'concept': 'spontaneous',
        'concept_selection': 'auto',
        'workflow': FULL_SPONTANEOUS
    }

    print("3. Building full session export archive (PPTX, GIF, HTML games, Host guide)...")
    export = build_session_export(metadata, brief, toolkit)
    print(f"   Export built successfully! Archive size: {len(export.archive):,} bytes")

    draft = {
        'metadata': metadata,
        'brief': brief,
        'toolkit': toolkit,
        'event_toolkit': toolkit
    }
    revision = export_revision(draft)
    save_run(draft, package=export.archive, export_revision=revision)
    print("4. Saved run to user_data/last_run.zip!")
    print("   ALL DONE! The whole 25-slide presentation is ready in TalkLine Studio.")


if __name__ == '__main__':
    main()
