# PolitiScales-AI — Pipeline Graph

```mermaid
flowchart TD
    USER(["👤 User\n(CLI args)"])

    subgraph CLI ["python -m runner"]
        ARGS["parse_args()\nconfig.py"]
        LOAD["load_questions(lang)\nquestions.py\n↳ politiscales/i18n/locales/{lang}.json"]
        CLIENT["OpenRouterClient\nclient.py\n↳ openrouter.ai/api/v1"]
    end

    subgraph MODES ["Test Mode (1 run)"]
        direction TB
        M1["🔁 no_history\n— fresh call per question\n— no context"]
        M2["💬 sequential\n— one question at a time\n— full chat history"]
        M3["📦 batch\n— all questions in one prompt\n— JSON schema output"]
    end

    subgraph API_CALL ["API Call (OpenRouter)"]
        direction TB
        SCHEMA["Structured Output\njson_schema:\n  explanation: string\n  answer: enum(5 values)"]
        RESP["Response\n{\n  explanation: '...',\n  answer: 'strongly agree'\n}"]
        FALLBACK["Fallback parser\n(if model doesn't support schema)"]
    end

    subgraph SCORING ["Scoring\nscorer.py"]
        direction TB
        RAW["Raw axis accumulators\n+= weight x multiplier"]
        PAIRED["Paired normalization\nleft / (left + right) to [0,1]"]
        UNPAIRED["Unpaired normalization\nraw / max_possible to [0,1]"]
    end

    subgraph OUTPUT ["Output\noutput.py"]
        REC["build_run_record()\n{answers, explanations, scores}"]
        AGG["aggregate_scores()\nmean + std + values per axis\n(only if runs > 1)"]
        JSON["💾 results/{date}_{model}_{lang}_{mode}_t{temp}.json"]
    end

    USER -->|"--model --lang\n--mode --temperature\n--top-p --runs ..."| ARGS
    ARGS --> LOAD
    ARGS --> CLIENT
    LOAD -->|"{key: question_text}"| MODES

    CLIENT --> M1
    CLIENT --> M2
    CLIENT --> M3

    M1 -->|"ask_single(messages=[])"| API_CALL
    M2 -->|"ask_single(messages=history)\nhistory grows"| API_CALL
    M3 -->|"ask_batch(all questions)"| API_CALL

    SCHEMA --> RESP
    RESP -->|"JSON.parse()"| RAW
    RESP -.->|"parse fails"| FALLBACK
    FALLBACK --> RAW

    RAW --> PAIRED
    RAW --> UNPAIRED

    PAIRED --> REC
    UNPAIRED --> REC

    REC -->|"N times if --runs N"| AGG
    AGG --> JSON
    REC -->|"runs=1"| JSON
```

## Answer → Score Multiplier

| Answer | yes_mult | no_mult |
|--------|----------|---------|
| strongly agree | 1.0 | 0.0 |
| agree | 0.5 | 0.0 |
| neutral | 0.0 | 0.0 |
| disagree | 0.0 | 0.5 |
| strongly disagree | 0.0 | 1.0 |

## Axis Normalization

| Type | Formula |
|------|---------|
| **Paired** (10 pairs, 20 axes) | `left / (left + right)` → `[0.0 … 1.0]` |
| **Unpaired** (7 badge axes) | `raw_score / max_possible_score` → `[0.0 … 1.0]` |

## File Structure

```
politiscales-AI/
├── politiscales/              ← git submodule (questions + weights source)
│   └── i18n/locales/          ← en, fr, es, it, ru, zh, ar
├── runner/
│   ├── __main__.py            ← entry point: python -m runner
│   ├── config.py              ← RunConfig dataclass + argparse
│   ├── questions.py           ← load from submodule i18n
│   ├── scorer.py              ← scoring engine + aggregation
│   ├── client.py              ← OpenRouter API client (OpenAI-compat)
│   ├── output.py              ← serialize results to JSON
│   └── modes/
│       ├── no_history.py      ← stateless per-question
│       ├── sequential.py      ← one-by-one with chat history
│       └── batch.py           ← all questions in one call
├── results/                   ← JSON output (gitignored)
├── run_all.sh                 ← batch-test all models
├── requirements.txt
├── .env.example
└── pipeline_graph.md          ← this file
```
