
from runner.config import parse_args, SYSTEM_PROMPTS
import sys

def test_lang(lang):
    sys.argv = ["runner", "--lang", lang, "--dry-run"]
    config = parse_args()
    print(f"LANGUAGE: {lang}")
    print(f"PROMPT START: {config.system_prompt[:100]}...")
    print("-" * 20)

test_lang("fr")
test_lang("ar")
test_lang("zh")
test_lang("en")
