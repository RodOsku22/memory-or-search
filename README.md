# Memory or Search?

**Where do AI brand recommendations come from: what a model remembers, or what it finds when it searches?**

A one-night pilot by Rod Oskouian, built with Claude Code. The same buyer questions go to each engine twice, once with web search off (the model can only use its training data) and once with search on. Comparing the two separates a brand's visibility in a model's memory from its visibility after retrieval.

Read the report: `docs/index.html` (published with GitHub Pages).

## Design

- **Categories and prompts:** the four categories and "Recommend X." prompts from Petra Labs' study *Comparing Search Behavior and Brand Visibility Across Generative Engines* (Sep 2026), plus one situational version of each prompt.
- **Engines (API):** OpenAI `gpt-5.5` (reasoning off), Anthropic `claude-sonnet-5`, Google `gemini-3.5-flash-lite` (memory only; the free tier allows no search calls).
- **Runs:** 907 answers collected Nov 9, 2026. 15 runs per cell for ChatGPT, 18–30 for Claude, 30 for Gemini.
- **Statistics:** visibility as a share of answering runs; bootstrap 95% CIs and permutation tests per brand, Benjamini–Hochberg corrected; total variation distance between brand profiles against a permutation noise floor.

## Pilot findings (directional)

1. Turning search on moved the brand mix beyond run-to-run noise in all 16 category × engine × prompt cells.
2. ChatGPT's search-on answers mostly confirm its memory (mean rank correlation 0.86); Claude's reshuffle it (0.63).
3. On broad prompts in 3 of 4 categories, ChatGPT and Claude agree more from memory (9–16 point mean range) than after search (23–36). Secured credit cards run the other way.
4. The expected difference between broad and situational prompts did not appear (mean TVD 0.27 vs 0.29).

Limitations, examples and implications are in the report.

## Reproduce

    pip install httpx numpy pandas
    export OPENAI_API_KEY=... ANTHROPIC_API_KEY=... GOOGLE_API_KEY=...
    python src/check.py                  # confirm models and request shapes
    python src/run.py --runs 30          # resumable; writes data/runs*.jsonl
    python src/analyze.py                # data/results.json and CSV tables
    python report/make_narrative.py && python report/build.py

## Files

| Path | Contents |
|---|---|
| `src/config.py` | Prompts, brand vocabularies, engines |
| `src/engines.py` | API adapters for search off / on |
| `src/run.py` | Resumable, balanced runner |
| `src/analyze.py` | Brand extraction and statistics |
| `data/runs.jsonl` | Claude answers (raw) |
| `data/runs_openai.jsonl` | ChatGPT answers (raw) |
| `data/runs_gemini.jsonl` | Gemini memory answers (raw) |
| `data/pilot_openai_default_settings.jsonl` | First ChatGPT pilot at default settings, excluded from analysis |
| `data/*.csv`, `data/results.json` | Analysis outputs |
| `report/` | Page template and build scripts |
| `docs/index.html` | The published report |

Independent work. Not affiliated with or endorsed by Petra Labs.
