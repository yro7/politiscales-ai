# PolitiScales-AI

> Make any AI model take the [PolitiScales](https://politiscales.party/) political test.  
> Compare models across axes, languages, and prompt strategies.

## Features

- **14+ models** via a single [OpenRouter](https://openrouter.ai/) API key (GPT, Gemini, DeepSeek, Claude, Mistral, Llama, Grok…)
- **7 languages**: `en` `fr` `es` `it` `ru` `zh` `ar`
- **3 test modes**: `no_history` · `sequential` · `batch`
- **Structured output** — every answer includes an `explanation` + one of the 5 official PolitiScales responses
- **Configurable**: temperature, top-p, max-tokens, system prompt, number of runs
- **Multi-run aggregation** — run N times and get mean ± std per axis in a single JSON file
- **Results Visualization** — generate beautiful, PolitiScales-style results cards (PNG) with Pillow
- **Fine-grained Scoring** — support for the **Neutral** axis in both individual runs and aggregates
- **Error Auditing** — track exactly which questions failed to parse and triggered fallbacks via `fallback_keys`
- **Dry-run mode** — inspect prompts without consuming API credits

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your OpenRouter API key
cp .env.example .env
# edit .env and add your key from https://openrouter.ai/settings/keys

# 3. Run the test
python -m runner --model openai/gpt-4.1 --lang en --mode sequential

# 4. Generate visualization for existing results
python -c "from runner.display import generate_results_card; import json; from pathlib import Path; p = Path('results/your_file.json'); generate_results_card(json.loads(p.read_text()), p.with_suffix('.png'))"

# 5. Dry-run to inspect prompts
python -m runner --model openai/gpt-4.1 --lang fr --mode batch --dry-run
```

## CLI Reference

```
python -m runner [options]

Options:
  --model MODEL           Model ID in provider/model format (default: openai/gpt-4.1)
  --lang LANG             Language: en fr es it ru zh ar (default: en)
  --mode MODE             no_history | sequential | batch (default: sequential)
  --temperature FLOAT     Sampling temperature 0.0–2.0 (default: 0.7)
  --max-tokens INT        Max tokens per response (default: 512)
  --top-p FLOAT           Nucleus sampling (default: 1.0)
  --system-prompt STR     Override the system instruction
  --runs INT              Repeat N times, aggregate into one file (default: 1)
  --output-dir DIR        Where to save results (default: ./results)
  --dry-run               Print prompts without calling the API
  --notes STR             Freeform notes stored in result metadata
  --api-key KEY           OpenRouter API key (or set OPENROUTER_API_KEY env var)
```

## Test Modes

| Mode | Description |
|------|-------------|
| `no_history` | Each question is a **fresh API call** — no memory of previous answers |
| `sequential` | Questions asked **one-by-one** with full chat history — model stays consistent |
| `batch` | **All 117 questions at once** — single API call, structured JSON response |

## Output Format

{
  "meta": {
    "model": "openai/gpt-4.1",
    "total_fallbacks": 2,
    "fallback_keys": ["constructivism_becoming_woman", "culture_religion"],
    ...
  },
  "runs": [
    {
      "run_id": 1,
      "answers": { ... },
      "scores": {
        "paired": {
          "identity": { "constructivism": 0.81, "essentialism": 0.14, "neutral": 0.05 }
        },
        "unpaired": { "anarchism": 0.0 }
      },
      "fallback_keys": ["constructivism_becoming_woman"]
    }
  ],
  "aggregate": {
    "runs_count": 1,
    "paired": {
      "identity": {
        "constructivism": { "mean": 0.81, "std": null, "values": [0.81] },
        "essentialism": { "mean": 0.14, "std": null, "values": [0.14] },
        "neutral": { "mean": 0.05, "std": null, "values": [0.05] }
      }
    }
  }
}
```

## Visualization

Every run generates a JSON and a corresponding PNG results card. The card includes:
- **Flag generation** — dominant axes colors and symbols.
- **Axis bars** — 3-segment bars (Left, Neutral, Right) with percentages.
- **Badges** — special badges (Anarchism, Feminism, etc.) when thresholds are met.
- **Model Metadata** — provider logo and model details in the footer.

## Batch All Models

```bash
chmod +x run_all.sh
./run_all.sh en sequential 0.7
```

## Architecture

See [pipeline_graph.md](./pipeline_graph.md) for the full Mermaid flow diagram.

## Available Models

| Provider | Models |
|----------|--------|
| OpenAI | `openai/gpt-4.1` `openai/gpt-4.1-mini` `openai/gpt-4o` `openai/gpt-4.1-nano` |
| Google | `google/gemini-2.5-flash` `google/gemini-2.5-pro` |
| DeepSeek | `deepseek/deepseek-chat-v3-0324` `deepseek/deepseek-r1` |
| Anthropic | `anthropic/claude-sonnet-4` `anthropic/claude-haiku-3.5` `anthropic/claude-opus-4` |
| Mistral | `mistralai/mistral-large` `mistralai/mistral-small-3.1-24b-instruct` |
| Meta | `meta-llama/llama-4-maverick` `meta-llama/llama-4-scout` |
| xAI | `x-ai/grok-3` `x-ai/grok-3-mini` |
| Other | `qwen/qwen3-235b-a22b` `microsoft/phi-4` |

Any model string accepted by [OpenRouter](https://openrouter.ai/models) works with `--model`.
