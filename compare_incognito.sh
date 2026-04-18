#!/usr/bin/env bash
# compare_incognito.sh — Compare ChatGPT, Grok, Claude, and DeepSeek in incognito mode
# Usage: ./compare_incognito.sh

set -euo pipefail

MODELS=(
  "openai/gpt-4o"
  "x-ai/grok-3"
  "anthropic/claude-sonnet-4"
  "deepseek/deepseek-chat-v3-0324"
)

LANG="en"
MODE="no_history"
PROMPT_TYPE="incognito"
TEMP="0.7"
RUNS="3"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Running Benchmark for all models"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 -m runner \
  --model "${MODELS[@]}" \
  --lang "$LANG" \
  --mode "$MODE" \
  --prompt-type "$PROMPT_TYPE" \
  --temperature "$TEMP" \
  --runs "$RUNS"

echo "✅ Benchmark complete. Results and images are in ./results/"
