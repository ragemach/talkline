"""Run Round 1 generation check for a topic and inspect cards."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.spontaneous_content import regenerate_spontaneous_section, _demo_spontaneous
from src.business_content import regenerate_business_section, _demo_business
from src.spontaneous_deck import build_spontaneous_deck
from src.business_deck import build_business_deck
from src.spontaneous_demo_toolkit import demo_spontaneous_toolkit

def check_topic(topic: str, format_name: str = "spontaneous", output_file: str = None):
    print(f"Generating {format_name} Round 1 for: {topic!r}...")
    if format_name == "business":
        demo = _demo_business()
        res = regenerate_business_section(topic, demo, "round1", "qwen3:8b")
    else:
        demo = _demo_spontaneous()
        res = regenerate_spontaneous_section(topic, demo, "round1", "qwen3:8b")

    cards = res["round1"]
    print(f"Generated {len(cards)} cards successfully!\n")
    for i, c in enumerate(cards, 1):
        print(f"=== Card {i}: {c['title']} ===")
        print("  A2:", c["a2"])
        print("  B2:", c["b2"])
        print("  C1:", c["c1"])
        print()

    # Test rendering the deck
    print("Testing deck render...")
    if format_name == "business":
        deck_bytes = build_business_deck(topic, res, demo_spontaneous_toolkit(topic), "TalkLine_Game.html")
    else:
        deck_bytes = build_spontaneous_deck(topic, res)
    print(f"Deck rendered successfully! Size: {len(deck_bytes):,} bytes")

    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"topic": topic, "format": format_name, "model": "qwen3:8b", "round1": cards}, indent=2), encoding="utf-8")
        print(f"Saved to {output_file}")

    return res

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "What if city buses ran scheduled routes every hour all night?"
    fmt = sys.argv[2] if len(sys.argv) > 2 else "spontaneous"
    outfile = sys.argv[3] if len(sys.argv) > 3 else "output/round-one/hourly-night-buses-ollama-new.json"
    check_topic(topic, fmt, outfile)
