<h1 align="center">PolitiScales-AI</h1>

<p align="center">
  <strong>Make any AI model take the <a href="https://politiscales.party/">PolitiScales</a> political test.</strong><br>
  Compare models across axes, languages, and prompt strategies.
</p>

<p align="center">
  <img src="results/png/2026-04-18_09-37-38_openai-gpt-4.1_en_sequential_t0_70.png" width="32%" alt="GPT-4.1 Results">
  <img src="results/png/2026-04-18_10-09-00_x-ai-grok-3-mini_en_sequential_t0_70.png" width="32%" alt="Grok-3-Mini Results">
  <img src="results/png/2026-04-18_11-11-57_anthropic-claude-sonnet-4_en_no_history_t0_70.png" width="32%" alt="Claude 3.7 Sonnet Results">
</p>

---

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

# 3. Run a test
python -m runner --model openai/gpt-4o --lang en --mode sequential

# 4. Generate visualization for existing results
python -c "from runner.display import generate_results_card; import json; from pathlib import Path; p = Path('results/your_file.json'); generate_results_card(json.loads(p.read_text()), p.with_suffix('.png'))"

# 5. Dry-run to inspect prompts without calling the API
python -m runner --model openai/gpt-4o --lang fr --mode batch --dry-run
```

## CLI Reference

```bash
python -m runner [options]
```

| Option          | Description                                  | Default         |
| :-------------- | :------------------------------------------- | :-------------- |
| `--model MODEL` | Model ID in `provider/model` format          | `openai/gpt-4o` |
| `--lang LANG`   | Language: `en` `fr` `es` `it` `ru` `zh` `ar` | `en`            |
| `--mode MODE`   | `no_history` \| `sequential` \| `batch`      | `sequential`    |
| `--temperature` | Sampling temperature 0.0–2.0                 | `0.7`           |
| `--max-tokens`  | Max tokens per response                      | `512`           |
| `--runs INT`    | Repeat N times and aggregate results         | `1`             |
| `--output-dir`  | Directory to save results                    | `./results`     |
| `--dry-run`     | Print prompts without calling the API        | -               |

---

## 🧪 Test Modes

| Mode               | Description                                                                |
| :----------------- | :------------------------------------------------------------------------- |
| 🧊 **`no_history`** | Each question is a **fresh API call** — no memory of previous answers.     |
| 🔄 **`sequential`** | Questions asked **one-by-one** with full chat history — keeps context.     |
| 📦 **`batch`**      | **All 117 questions at once** — single API call, structured JSON response. |

## Output Format

Results are saved as structured JSON. An aggregate run looks like this:

```json
{
  "meta": {
    "model": "openai/gpt-4o",
    "total_fallbacks": 2,
    "fallback_keys": ["constructivism_becoming_woman", "culture_religion"]
  },
  "aggregate": {
    "paired": {
      "identity": {
        "constructivism": { "mean": 0.81, "std": 0.02 },
        "essentialism": { "mean": 0.14, "std": 0.01 },
        "neutral": { "mean": 0.05, "std": 0.01 }
      }
    }
  }
}
```

---

## 🎨 Visualization

Every run generates a JSON and a corresponding **PNG results card**. The card includes:

- 🏳️ **Flag generation** — dominant axes colors and symbols.
- 📉 **Axis bars** — 3-segment bars (Left, Neutral, Right) with percentages.
- 🎖️ **Badges** — special badges (Anarchism, Feminism, etc.) when thresholds are met.
- 🤖 **Model Metadata** — provider logo and model details in the footer.

---

## Batch All Models

To run every supported model in a specific language:

```bash
chmod +x run_all.sh
./run_all.sh en sequential 0.7
```

## Architecture

See [pipeline_graph.md](./pipeline_graph.md) for the full Mermaid flow diagram.

## 🤖 Available Models

| Provider      | Models                                                                               |
| :------------ | :----------------------------------------------------------------------------------- |
| **OpenAI**    | `openai/gpt-4o` `openai/gpt-4o-mini` `openai/gpt-4-turbo`                            |
| **Google**    | `google/gemini-2.0-flash` `google/gemini-2.0-pro`                                    |
| **DeepSeek**  | `deepseek/deepseek-chat` `deepseek/deepseek-reasoner`                                |
| **Anthropic** | `anthropic/claude-3-7-sonnet` `anthropic/claude-3-5-haiku` `anthropic/claude-3-opus` |
| **Mistral**   | `mistralai/mistral-large` `mistralai/pixtral-large`                                  |
| **Meta**      | `meta-llama/llama-3.3-70b-instruct` `meta-llama/llama-3.1-405b`                      |
| **xAI**       | `x-ai/grok-2` `x-ai/grok-beta`                                                       |
| **Qwen**      | `qwen/qwen-2.5-72b-instruct` `qwen/qwen-max`                                         |

---

> [!TIP]
> Any model string accepted by [OpenRouter](https://openrouter.ai/models) works with the `--model` flag.
