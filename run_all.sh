#!/usr/bin/env bash
# run_all.sh — batch-test all major models in a given language + mode
# Usage: ./run_all.sh [lang] [mode] [temperature]
# Example: ./run_all.sh en sequential 0.7

set -euo pipefail

TEST_LANG="${1:-en}"
MODE="${2:-sequential}"
TEMP="${3:-0.7}"

MODELS=(
  # OpenAI
  "openai/gpt-4.1"
  "openai/gpt-4.1-mini"
  "openai/gpt-4o"
  # Google
  "google/gemini-2.5-flash"
  "google/gemini-2.5-pro"
  # DeepSeek
  "deepseek/deepseek-chat-v3-0324"
  "deepseek/deepseek-r1"
  # Anthropic
  "anthropic/claude-sonnet-4"
  "anthropic/claude-haiku-3.5"
  # Mistral
  "mistralai/mistral-large"
  # Meta
  "meta-llama/llama-4-maverick"
  "meta-llama/llama-4-scout"
  # xAI
  "x-ai/grok-3"
  # Other
  "qwen/qwen3-235b-a22b"
)

echo "🏛️  PolitiScales-AI — batch run"
echo "   lang=${TEST_LANG}  mode=${MODE}  temperature=${TEMP}"
echo "   models: ${#MODELS[@]}"
echo ""

if ! python3 -m runner \
  --model "${MODELS[@]}" \
  --lang "$TEST_LANG" \
  --mode "$MODE" \
  --temperature "$TEMP"; then
  echo "⚠️  Batch run failed"
  exit 1
fi

echo "✅  All done. Results in ./results/"
