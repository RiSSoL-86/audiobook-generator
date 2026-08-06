# Audiobook-generator

Generate an audiobook from a PDF: text extraction, chapter and chunk
splitting, Soniox TTS narration, and per-chapter MP3 merging.

The pipeline runs in five ordered stages:

| # | Stage      | What it does                                  |
|---|------------|-----------------------------------------------|
| 1 | `extract`  | Extract raw text from the PDF (LlamaParse)    |
| 2 | `chapters` | Split cleaned text into chapters (TOC-driven) |
| 3 | `chunk`    | Split each chapter into TTS-sized blocks      |
| 4 | `tts`      | Voice every chunk via Soniox                  |
| 5 | `merge`    | Concatenate chunks into one MP3 per chapter   |

## Requirements

- **Python 3.14+**
- **[uv](https://docs.astral.sh/uv/)** for dependency management
- **ffmpeg / ffprobe** on `PATH` (used by the merge stage)
- API keys for **Soniox** (TTS) and **LlamaCloud** (extraction)

## Install

```bash
make install   # uv sync --locked
```

## Configure

Copy `src/.env.example` to `src/.env` and fill in the two required API keys
(`EXTRACT_LLAMA_CLOUD_API_KEY`, `TTS_SONIOX_API_KEY`); everything else has
sensible defaults.

```bash
cp src/.env.example src/.env
```

## Run

The entry point is `src/main.py`. Run it with `uv run`:

```bash
uv run python src/main.py --input input/book.pdf --output output/book
```

This runs the full pipeline (`extract` → `merge`) and writes the result tree
(text, chunks, audio, MP3s, and a `manifest.json`) into the output folder.

### Options

| Option         | Default   | Description                                   |
|----------------|-----------|-----------------------------------------------|
| `--input`      | required  | Source PDF file                               |
| `--output`     | required  | Output folder for this book                   |
| `--from-stage` | `extract` | First stage to run                            |
| `--to-stage`   | `merge`   | Last stage to run                             |
| `--chapter`    | all       | Limit the run to a single chapter (by index)  |
| `--force`      | off       | Rerun stages, ignoring cached results         |
| `--dry-run`    | off       | Log actions without writing any files         |

Stage values for `--from-stage` / `--to-stage`: `extract`, `chapters`,
`chunk`, `tts`, `merge`.

### Examples

```bash
# Only re-detect chapters (stage 2), overwriting previous output
uv run python src/main.py --input input/book.pdf --output output/book \
  --from-stage chapters --to-stage chapters --force

# Voice and merge just chapter 3
uv run python src/main.py --input input/book.pdf --output output/book \
  --from-stage tts --chapter 3

# Preview what would run, without side effects
uv run python src/main.py --input input/book.pdf --output output/book --dry-run
```

The pipeline is resumable: each stage skips work that is already present in the
output folder, so re-running the command continues where it left off (use
`--force` to redo a stage).

## Development

```bash
make install   # sync locked dependencies
make lint      # ruff format + ruff check + mypy
make test      # pytest
```
