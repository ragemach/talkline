"""Explicit local-model integration check; writes UTF-8, prints ASCII status only."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.toolkit import generate_toolkit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='Office Boundaries')
    parser.add_argument('--export', action='store_true', help='Also build readable HTML and editable PPTX locally')
    args = parser.parse_args()
    result = generate_toolkit(args.topic)
    folder = ROOT / 'output'
    folder.mkdir(exist_ok=True)
    path = folder / 'toolkit-reviewed.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved output/toolkit-reviewed.json as UTF-8')
    print('Review status:', result['review_status'])
    print('Review findings:', len(result.get('review', {}).get('issues', [])))
    if args.export:
        from src.toolkit_pptx import build_toolkit_pptx
        from src.toolkit_export import toolkit_html
        export_folder = folder / 'toolkit-local-smoke'
        export_folder.mkdir(exist_ok=True)
        (export_folder / 'Toolkit.pptx').write_bytes(build_toolkit_pptx(result))
        (export_folder / 'Toolkit.html').write_text(toolkit_html(result), encoding='utf-8')
        print('Exported output/toolkit-local-smoke/Toolkit.pptx and Toolkit.html')
    return 0 if result['review_status'] == 'local_review_complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
