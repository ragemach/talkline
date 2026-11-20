"""Rebuild the Spontaneous Talk reference inventory using local tools."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.template_blueprints import inspect_spontaneous_template


if __name__ == '__main__':
    source = ROOT / 'references/Completed_Spontaneous_Talk_23_Slides_READABLE.pptx'
    destination = ROOT / 'templates/spontaneous.blueprint.json'
    blueprint = inspect_spontaneous_template(source)
    destination.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2),
                           encoding='utf-8')
    print(f'Catalogued {len(blueprint["slides"])} reference slides.')
