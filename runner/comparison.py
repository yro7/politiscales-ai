"""
Comparison helpers for running benchmarks across multiple parameter values.
"""
from __future__ import annotations

import itertools
from typing import Any, Callable, List, Tuple

from runner.config import (
    RunConfig, 
    SUPPORTED_LANGUAGES, 
    SUPPORTED_MODES, 
    SUPPORTED_PROMPT_TYPES,
    get_default_system_prompt
)

def get_comparison_grid(base_config: RunConfig) -> List[RunConfig]:
    """
    Generate a list of RunConfig objects based on comparison flags.
    If multiple flags are set, it generates a Cartesian product.
    """
    langs = SUPPORTED_LANGUAGES if base_config.compare_langs else [base_config.language]
    modes = SUPPORTED_MODES if base_config.compare_modes else [base_config.mode]
    prompts = SUPPORTED_PROMPT_TYPES if base_config.compare_prompts else [base_config.prompt_type]

    grid = []
    for lang, mode, p_type in itertools.product(langs, modes, prompts):
        # Create a copy and adjust
        new_config = RunConfig(**{k: v for k, v in base_config.__dict__.items()})
        new_config.language = lang
        new_config.mode = mode
        new_config.prompt_type = p_type
        
        # Reset comparison flags in the generated configs to avoid recursion if they were passed around
        new_config.compare_langs = False
        new_config.compare_modes = False
        new_config.compare_prompts = False

        # Automatically re-resolve system prompt if it was using the default
        # We assume if the current system_prompt matches the default for the OLD config, 
        # we should update it for the NEW config.
        # Actually, a safer way: if the user didn't PROVIDE one in CLI, we always re-resolve.
        # But RunConfig doesn't track if it was provided.
        # Let's check if the current system_prompt is the default for the BASE config params.
        old_default = get_default_system_prompt(base_config.prompt_type, base_config.language)
        if base_config.system_prompt == old_default:
            new_config.system_prompt = get_default_system_prompt(p_type, lang)
            
        grid.append(new_config)
    
    return grid

def print_comparison_summary(results: List[Tuple[RunConfig, dict]]) -> None:
    """
    Print a summary table comparing results across multiple runs.
    Each result is a tuple (config, payload).
    """
    if not results:
        return

    print("\n" + "="*80)
    print(" COMPARISON SUMMARY TABLE")
    print("="*80)

    # Pick axes to display (the 8 main paired ones)
    main_pairs = ["identity", "justice", "culture", "globalism", "economy", "markets", "environment", "radicalism"]
    
    # Header
    header = f"{'Language':<10} | {'Mode':<12} | {'Prompt':<10}"
    for pair in main_pairs:
        header += f" | {pair[:4]:<5}"
    print(header)
    print("-" * len(header))

    for config, payload in results:
        aggregate = payload.get("aggregate", {})
        paired = aggregate.get("paired", {})
        
        row = f"{config.language:<10} | {config.mode:<12} | {config.prompt_type:<10}"
        
        for pair_name in main_pairs:
            pair_data = paired.get(pair_name, {})
            # We take the first axis of the pair as a representative score (usually the first is the 'left' one)
            # Or better, show both? No, table will be too wide. 
            # Let's show the 'left' axis mean score.
            # We need to know the axis name.
            from runner.scorer import PAIRED_AXES
            left_axis = PAIRED_AXES[pair_name][0]
            score_data = pair_data.get(left_axis, {})
            mean = score_data.get("mean", 0.0)
            row += f" | {mean:.2f}"
            
        print(row)
    print("="*80 + "\n")

# Helpers requested by user (individual ones)
def compare_languages(config: RunConfig, run_fn: Callable) -> List[dict]:
    new_config = RunConfig(**{k: v for k, v in config.__dict__.items()})
    new_config.compare_langs = True
    return [run_fn(cfg) for cfg in get_comparison_grid(new_config)]

def compare_modes(config: RunConfig, run_fn: Callable) -> List[dict]:
    new_config = RunConfig(**{k: v for k, v in config.__dict__.items()})
    new_config.compare_modes = True
    return [run_fn(cfg) for cfg in get_comparison_grid(new_config)]

def compare_sysprompt(config: RunConfig, run_fn: Callable) -> List[dict]:
    new_config = RunConfig(**{k: v for k, v in config.__dict__.items()})
    new_config.compare_prompts = True
    return [run_fn(cfg) for cfg in get_comparison_grid(new_config)]
