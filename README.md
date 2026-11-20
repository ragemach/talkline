# TalkLine Studio

TalkLine Studio builds a reusable English-speaking session kit on your own computer. Enter a topic and event details. The app uses local Ollama to write the content and supplied TalkLine templates to make the editable PowerPoint, offline games, invitation GIF and ZIP. Demo mode runs without an AI model.

## Run on Windows 11

1. Clone or download this repository and open the extracted folder.
2. Install Python 3.14 and LibreOffice if they are missing.
3. Double-click `START_WINDOWS.bat`. It creates a virtual environment and installs the app's Python dependencies on first launch.
4. Open [TalkLine Studio](http://127.0.0.1:8501). Choose **Demo (offline)** and **Spontaneous Talk**, enter a topic, then generate and export.
5. For your own AI-written content, install Ollama and download a local model. The Windows setup was exercised with Python 3.14.5 and `qwen3:8b`. See the [local Ollama guide](docs/LOCAL_AI_FA.md).

Internet is needed for the initial downloads. Routine generation and ZIP export run locally. The published feedback form requires internet when opened.

## What works today

- **Spontaneous Talk** creates an editable deck, a levelled Toolkit, ten tiered discussion cards, a 40-card offline Patch Notes game, an invitation and a host guide.
- **Toolkit** keeps A1/A2, B1 and B2/C1 in separate groups. Vocabulary, phrases and idioms include Turkish meanings and English usage examples. Mini grammar gets separate slides.
- **Invitations** use one of the supplied styles and keep the source aspect ratio. The ZIP includes the editable invitation, a still image and an animated GIF.
- **Save and resume** reopens the last saved draft and matching ZIP. An interrupted Spontaneous Talk generation can resume from the last completed batch for the same topic and model.
- **Other concepts** are in development and still use the shorter prototype in the app. Game Night and Business English have separate offline game exporters under development.

Extract the ZIP before opening the PowerPoint or host guide so their relative game links work. Review generated English and Turkish before presenting.

## Development

See the [product specification](docs/PRODUCT_SPEC.md), [implementation roadmap](docs/IMPLEMENTATION_ROADMAP.md) and [vocabulary and grammar sources](docs/LEARNING_SOURCES.md). Original handoff and setup notes are in [docs](docs/).

After the Windows launcher creates the virtual environment, install the development dependencies and run the automated tests from PowerShell.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```
