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

echo "🧪 Incognito Comparison Benchmark"
echo "   Settings: lang=$LANG, mode=$MODE, type=$PROMPT_TYPE, temp=$TEMP, runs=$RUNS"
echo ""

for MODEL in "${MODELS[@]}"; do
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🚀 Running: $MODEL ($RUNS runs)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  python3 -m runner \
    --model "$MODEL" \
    --lang "$LANG" \
    --mode "$MODE" \
    --prompt-type "$PROMPT_TYPE" \
    --temperature "$TEMP" \
    --runs "$RUNS"
    
  echo ""
done

echo "✅ Benchmark complete. Results and images are in ./results/"
