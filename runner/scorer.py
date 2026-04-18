"""
Scoring engine — Python port of questions-weights.ts + axes.ts logic.

Axes:
  Paired  (10 pairs → 20 axes): each pair normalized to [0, 1]
  Unpaired (7 axes): normalized by max possible score per axis
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Answer value → multiplier
# ---------------------------------------------------------------------------
ANSWER_MULTIPLIERS: Dict[str, Tuple[float, float]] = {
    # (yes_mult, no_mult)
    "strongly agree":    (1.0, 0.0),
    "agree":             (0.5, 0.0),
    "neutral":           (0.0, 0.0),
    "disagree":          (0.0, 0.5),
    "strongly disagree": (0.0, 1.0),
}

# ---------------------------------------------------------------------------
# Paired axes (pair_name → (left_axis, right_axis))
# ---------------------------------------------------------------------------
PAIRED_AXES: Dict[str, Tuple[str, str]] = {
    "identity":    ("constructivism", "essentialism"),
    "justice":     ("rehabilitative_justice", "punitive_justice"),
    "culture":     ("progressive", "conservative"),
    "globalism":   ("internationalism", "nationalism"),
    "economy":     ("communism", "capitalism"),
    "markets":     ("regulation", "laissez_faire"),
    "environment": ("ecology", "production"),
    "radicalism":  ("revolution", "reform"),
    "perspective": ("materialism", "idealism"),       # no questions yet in weights
    "development": ("sustainability", "growth_at_all_costs"),  # no questions yet
}

# Unpaired axes and their badge thresholds (from axes.ts)
UNPAIRED_AXES: Dict[str, float] = {
    "anarchism":  0.9,
    "pragmatism": 0.5,
    "feminism":   0.9,
    "complotism": 0.9,
    "veganism":   0.5,
    "monarchism": 0.5,
    "religion":   0.5,
}

# ---------------------------------------------------------------------------
# Full question weights — ported from questions-weights.ts
# ---------------------------------------------------------------------------
QUESTIONS_WEIGHTS: Dict[str, Dict[str, List[Dict]]] = {
    # Constructivism / Essentialism
    "constructivism_becoming_woman": {
        "valuesYes": [{"axis": "constructivism", "value": 3}, {"axis": "feminism", "value": 3}],
        "valuesNo":  [{"axis": "essentialism",   "value": 3}],
    },
    "constructivism_racism_presence": {
        "valuesYes": [{"axis": "constructivism", "value": 3}],
        "valuesNo":  [{"axis": "essentialism",   "value": 3}],
    },
    "constructivism_science_society": {
        "valuesYes": [{"axis": "constructivism", "value": 3}],
        "valuesNo":  [{"axis": "essentialism",   "value": 3}],
    },
    "constructivism_gender_categories": {
        "valuesYes": [{"axis": "constructivism", "value": 3}, {"axis": "feminism", "value": 3}],
        "valuesNo":  [{"axis": "essentialism",   "value": 3}],
    },
    "constructivism_criminality_nature": {
        "valuesYes": [{"axis": "constructivism", "value": 3}],
        "valuesNo":  [{"axis": "essentialism",   "value": 3}],
    },
    "constructivism_sexual_orientation": {
        "valuesYes": [{"axis": "constructivism", "value": 3}],
        "valuesNo":  [{"axis": "essentialism",   "value": 3}],
    },
    "constructivism_ethnic_differences": {
        "valuesYes": [{"axis": "constructivism", "value": 3}],
        "valuesNo":  [{"axis": "essentialism",   "value": 3}],
    },
    "essentialism_gender_biology": {
        "valuesYes": [{"axis": "essentialism", "value": 3}],
        "valuesNo":  [{"axis": "constructivism", "value": 3}, {"axis": "feminism", "value": 3}],
    },
    "essentialism_hormones_character": {
        "valuesYes": [{"axis": "essentialism", "value": 3}],
        "valuesNo":  [{"axis": "constructivism", "value": 3}, {"axis": "feminism", "value": 3}],
    },
    "essentialism_sexual_aggression": {
        "valuesYes": [{"axis": "essentialism", "value": 3}],
        "valuesNo":  [{"axis": "constructivism", "value": 3}, {"axis": "feminism", "value": 3}],
    },
    "essentialism_transgender_identity": {
        "valuesYes": [{"axis": "essentialism",   "value": 3}],
        "valuesNo":  [{"axis": "constructivism", "value": 3}],
    },
    "essentialism_national_traits": {
        "valuesYes": [{"axis": "essentialism",   "value": 3}],
        "valuesNo":  [{"axis": "constructivism", "value": 3}],
    },
    "essentialism_human_heterosexuality": {
        "valuesYes": [{"axis": "essentialism",   "value": 3}],
        "valuesNo":  [{"axis": "constructivism", "value": 3}],
    },
    "essentialism_human_egoism": {
        "valuesYes": [{"axis": "essentialism",   "value": 3}],
        "valuesNo":  [{"axis": "constructivism", "value": 3}],
    },

    # Internationalism / Nationalism
    "internationalism_border_removal": {
        "valuesYes": [{"axis": "internationalism", "value": 3}],
        "valuesNo":  [{"axis": "nationalism",       "value": 3}],
    },
    "internationalism_ideals_country": {
        "valuesYes": [{"axis": "internationalism", "value": 3}],
        "valuesNo":  [{"axis": "nationalism",       "value": 3}],
    },
    "internationalism_country_reparation": {
        "valuesYes": [{"axis": "internationalism", "value": 3}],
        "valuesNo":  [{"axis": "nationalism",       "value": 3}],
    },
    "internationalism_free_trade_similarity": {
        "valuesYes": [{"axis": "internationalism", "value": 3}],
        "valuesNo":  [{"axis": "nationalism",       "value": 3}],
    },
    "internationalism_sport_chauvinism": {
        "valuesYes": [{"axis": "internationalism", "value": 3}],
        "valuesNo":  [{"axis": "nationalism",       "value": 3}],
    },
    "internationalism_global_concern": {
        "valuesYes": [{"axis": "internationalism", "value": 3}],
        "valuesNo":  [{"axis": "nationalism",       "value": 3}],
    },
    "internationalism_foreign_political_rights": {
        "valuesYes": [{"axis": "internationalism", "value": 3}],
        "valuesNo":  [{"axis": "nationalism",       "value": 3}],
    },
    "nationalism_citizen_priority": {
        "valuesYes": [{"axis": "nationalism",       "value": 3}],
        "valuesNo":  [{"axis": "internationalism", "value": 3}],
    },
    "nationalism_country_values": {
        "valuesYes": [{"axis": "nationalism",       "value": 3}],
        "valuesNo":  [{"axis": "internationalism", "value": 3}],
    },
    "nationalism_multiculturalism_danger": {
        "valuesYes": [{"axis": "nationalism",       "value": 3}],
        "valuesNo":  [{"axis": "internationalism", "value": 3}],
    },
    "nationalism_good_citizen_patriot": {
        "valuesYes": [{"axis": "nationalism",       "value": 3}],
        "valuesNo":  [{"axis": "internationalism", "value": 3}],
    },
    "nationalism_military_intervention": {
        "valuesYes": [{"axis": "nationalism",       "value": 3}],
        "valuesNo":  [{"axis": "internationalism", "value": 3}],
    },
    "nationalism_history_national_belonging": {
        "valuesYes": [{"axis": "nationalism",       "value": 3}],
        "valuesNo":  [{"axis": "internationalism", "value": 3}],
    },
    "nationalism_country_research_access": {
        "valuesYes": [{"axis": "nationalism",       "value": 3}],
        "valuesNo":  [{"axis": "internationalism", "value": 3}],
    },

    # Communism / Capitalism
    "communism_wealth_ownership": {
        "valuesYes": [{"axis": "communism",  "value": 3}],
        "valuesNo":  [{"axis": "capitalism", "value": 3}],
    },
    "communism_private_labor_theft": {
        "valuesYes": [{"axis": "communism",  "value": 3}],
        "valuesNo":  [{"axis": "capitalism", "value": 3}],
    },
    "communism_public_health": {
        "valuesYes": [{"axis": "communism",  "value": 3}],
        "valuesNo":  [{"axis": "capitalism", "value": 3}],
    },
    "communism_public_energy_infrastructure": {
        "valuesYes": [{"axis": "communism",  "value": 3}],
        "valuesNo":  [{"axis": "capitalism", "value": 3}],
    },
    "communism_patents_nonexistence": {
        "valuesYes": [{"axis": "communism",  "value": 3}],
        "valuesNo":  [{"axis": "capitalism", "value": 3}],
    },
    "communism_production_rationing": {
        "valuesYes": [{"axis": "communism",  "value": 3}],
        "valuesNo":  [{"axis": "capitalism", "value": 3}],
    },
    "communism_labor_market_exploitation": {
        "valuesYes": [{"axis": "communism",  "value": 3}],
        "valuesNo":  [{"axis": "capitalism", "value": 3}],
    },
    "capitalism_profit_economy": {
        "valuesYes": [{"axis": "capitalism", "value": 3}],
        "valuesNo":  [{"axis": "communism",  "value": 3}],
    },
    "capitalism_merit_wealth_difference": {
        "valuesYes": [{"axis": "capitalism", "value": 3}],
        "valuesNo":  [{"axis": "communism",  "value": 3}],
    },
    "capitalism_private_schools_universities": {
        "valuesYes": [{"axis": "capitalism", "value": 3}],
        "valuesNo":  [{"axis": "communism",  "value": 3}],
    },
    "capitalism_relocation_production": {
        "valuesYes": [{"axis": "capitalism", "value": 3}],
        "valuesNo":  [{"axis": "communism",  "value": 3}],
    },
    "capitalism_rich_poor_acceptance": {
        "valuesYes": [{"axis": "capitalism", "value": 3}],
        "valuesNo":  [{"axis": "communism",  "value": 3}],
    },
    "capitalism_private_industry_sectors": {
        "valuesYes": [{"axis": "capitalism", "value": 3}],
        "valuesNo":  [{"axis": "communism",  "value": 3}],
    },
    "capitalism_private_banks": {
        "valuesYes": [{"axis": "capitalism", "value": 3}],
        "valuesNo":  [{"axis": "communism",  "value": 3}],
    },

    # Regulation / Laissez-faire
    "regulation_income_tax_redistribution": {
        "valuesYes": [{"axis": "regulation",    "value": 3}],
        "valuesNo":  [{"axis": "laissez_faire", "value": 3}],
    },
    "regulation_retirement_age": {
        "valuesYes": [{"axis": "regulation",    "value": 3}],
        "valuesNo":  [{"axis": "laissez_faire", "value": 3}],
    },
    "regulation_unjustified_dismissals": {
        "valuesYes": [{"axis": "regulation",    "value": 3}],
        "valuesNo":  [{"axis": "laissez_faire", "value": 3}],
    },
    "regulation_wage_control": {
        "valuesYes": [{"axis": "regulation",    "value": 3}],
        "valuesNo":  [{"axis": "laissez_faire", "value": 3}],
    },
    "regulation_monopoly_prevention": {
        "valuesYes": [{"axis": "regulation",    "value": 3}],
        "valuesNo":  [{"axis": "laissez_faire", "value": 3}],
    },
    "regulation_public_loans": {
        "valuesYes": [{"axis": "regulation",    "value": 3}],
        "valuesNo":  [{"axis": "laissez_faire", "value": 3}],
    },
    "regulation_sector_subsidies": {
        "valuesYes": [{"axis": "regulation",    "value": 3}],
        "valuesNo":  [{"axis": "laissez_faire", "value": 3}],
    },
    "laissez_faire_market_optimality": {
        "valuesYes": [{"axis": "laissez_faire", "value": 3}],
        "valuesNo":  [{"axis": "regulation",    "value": 3}],
    },
    "laissez_faire_contract_freedom": {
        "valuesYes": [{"axis": "laissez_faire", "value": 3}],
        "valuesNo":  [{"axis": "regulation",    "value": 3}],
    },
    "laissez_faire_labor_regulations": {
        "valuesYes": [{"axis": "laissez_faire", "value": 3}],
        "valuesNo":  [{"axis": "regulation",    "value": 3}],
    },
    "laissez_faire_working_hours": {
        "valuesYes": [{"axis": "laissez_faire", "value": 3}],
        "valuesNo":  [{"axis": "regulation",    "value": 3}],
    },
    "laissez_faire_environmental_standards": {
        "valuesYes": [{"axis": "laissez_faire", "value": 3}],
        "valuesNo":  [{"axis": "regulation",    "value": 3}],
    },
    "laissez_faire_social_assistance": {
        "valuesYes": [{"axis": "laissez_faire", "value": 3}],
        "valuesNo":  [{"axis": "regulation",    "value": 3}],
    },
    "laissez_faire_public_enterprises": {
        "valuesYes": [{"axis": "laissez_faire", "value": 3}],
        "valuesNo":  [{"axis": "regulation",    "value": 3}],
    },

    # Progressive / Conservative
    "progressive_tradition_questioning": {
        "valuesYes": [{"axis": "progressive",  "value": 3}],
        "valuesNo":  [{"axis": "conservative", "value": 3}],
    },
    "progressive_official_languages": {
        "valuesYes": [{"axis": "progressive",  "value": 3}],
        "valuesNo":  [{"axis": "conservative", "value": 3}],
    },
    "progressive_marriage_abolition": {
        "valuesYes": [{"axis": "progressive",  "value": 3}, {"axis": "feminism", "value": 3}],
        "valuesNo":  [{"axis": "conservative", "value": 3}],
    },
    "progressive_foreign_culture_enrichment": {
        "valuesYes": [{"axis": "progressive",  "value": 3}],
        "valuesNo":  [{"axis": "conservative", "value": 3}],
    },
    "progressive_religion_influence": {
        "valuesYes": [{"axis": "progressive",  "value": 3}],
        "valuesNo":  [{"axis": "conservative", "value": 3}],
    },
    "progressive_language_definition": {
        "valuesYes": [{"axis": "progressive",  "value": 3}],
        "valuesNo":  [{"axis": "conservative", "value": 3}],
    },
    "progressive_euthanasia_legalization": {
        "valuesYes": [{"axis": "progressive",  "value": 3}],
        "valuesNo":  [{"axis": "conservative", "value": 3}],
    },
    "conservative_homosexual_equality": {
        "valuesYes": [{"axis": "conservative", "value": 3}],
        "valuesNo":  [{"axis": "progressive",  "value": 3}],
    },
    "conservative_death_penalty_justification": {
        "valuesYes": [{"axis": "conservative",        "value": 3}, {"axis": "punitive_justice",      "value": 3}],
        "valuesNo":  [{"axis": "progressive",          "value": 3}, {"axis": "rehabilitative_justice", "value": 3}],
    },
    "conservative_technological_change": {
        "valuesYes": [{"axis": "conservative", "value": 3}],
        "valuesNo":  [{"axis": "progressive",  "value": 3}],
    },
    "conservative_school_curriculum": {
        "valuesYes": [{"axis": "conservative", "value": 3}],
        "valuesNo":  [{"axis": "progressive",  "value": 3}],
    },
    "conservative_abortion_restriction": {
        "valuesYes": [{"axis": "conservative", "value": 3}],
        "valuesNo":  [{"axis": "progressive",  "value": 3}, {"axis": "feminism", "value": 3}],
    },
    "conservative_couple_child_production": {
        "valuesYes": [{"axis": "conservative", "value": 3}],
        "valuesNo":  [{"axis": "progressive",  "value": 3}],
    },
    "conservative_abstinence_preference": {
        "valuesYes": [{"axis": "conservative", "value": 3}],
        "valuesNo":  [{"axis": "progressive",  "value": 3}],
    },

    # Ecology / Production
    "ecology_species_extinction": {
        "valuesYes": [{"axis": "ecology",     "value": 3}],
        "valuesNo":  [{"axis": "production",  "value": 3}],
    },
    "ecology_gmo_restriction": {
        "valuesYes": [{"axis": "ecology",     "value": 3}],
        "valuesNo":  [{"axis": "production",  "value": 3}],
    },
    "ecology_climate_change_combat": {
        "valuesYes": [{"axis": "ecology",     "value": 3}],
        "valuesNo":  [{"axis": "production",  "value": 3}],
    },
    "ecology_consumption_change": {
        "valuesYes": [{"axis": "ecology",     "value": 3}],
        "valuesNo":  [{"axis": "production",  "value": 3}],
    },
    "ecology_biodiversity_agriculture": {
        "valuesYes": [{"axis": "ecology",     "value": 3}],
        "valuesNo":  [{"axis": "production",  "value": 3}],
    },
    "ecology_ecosystem_preservation": {
        "valuesYes": [{"axis": "ecology",     "value": 3}],
        "valuesNo":  [{"axis": "production",  "value": 3}],
    },
    "ecology_waste_reduction_production": {
        "valuesYes": [{"axis": "ecology",     "value": 3}],
        "valuesNo":  [{"axis": "production",  "value": 3}],
    },
    "production_space_colonization": {
        "valuesYes": [{"axis": "production", "value": 3}],
        "valuesNo":  [{"axis": "ecology",    "value": 3}],
    },
    "production_ecosystem_transformation": {
        "valuesYes": [{"axis": "production", "value": 3}],
        "valuesNo":  [{"axis": "ecology",    "value": 3}],
    },
    "production_research_investment": {
        "valuesYes": [{"axis": "production", "value": 3}],
        "valuesNo":  [{"axis": "ecology",    "value": 3}],
    },
    "production_transhumanism_benefit": {
        "valuesYes": [{"axis": "production", "value": 3}],
        "valuesNo":  [{"axis": "ecology",    "value": 3}],
    },
    "production_nuclear_energy": {
        "valuesYes": [{"axis": "production", "value": 3}],
        "valuesNo":  [{"axis": "ecology",    "value": 3}],
    },
    "production_fossil_energy_exploitation": {
        "valuesYes": [{"axis": "production", "value": 3}],
        "valuesNo":  [{"axis": "ecology",    "value": 3}],
    },
    "production_economic_growth": {
        "valuesYes": [{"axis": "production", "value": 3}],
        "valuesNo":  [{"axis": "ecology",    "value": 3}],
    },

    # Rehabilitative Justice / Punitive Justice
    "rehabilitative_justice_prison_abolition": {
        "valuesYes": [{"axis": "rehabilitative_justice", "value": 3}],
        "valuesNo":  [{"axis": "punitive_justice",        "value": 3}],
    },
    "rehabilitative_justice_minimum_penalty": {
        "valuesYes": [{"axis": "rehabilitative_justice", "value": 3}],
        "valuesNo":  [{"axis": "punitive_justice",        "value": 3}],
    },
    "rehabilitative_justice_reinsertion_support": {
        "valuesYes": [{"axis": "rehabilitative_justice", "value": 3}],
        "valuesNo":  [{"axis": "punitive_justice",        "value": 3}],
    },
    "rehabilitative_justice_contextual_penalties": {
        "valuesYes": [{"axis": "rehabilitative_justice", "value": 3}],
        "valuesNo":  [{"axis": "punitive_justice",        "value": 3}],
    },
    "rehabilitative_justice_detainee_conditions": {
        "valuesYes": [{"axis": "rehabilitative_justice", "value": 3}],
        "valuesNo":  [{"axis": "punitive_justice",        "value": 3}],
    },
    "rehabilitative_justice_data_profiling": {
        "valuesYes": [{"axis": "rehabilitative_justice", "value": 3}],
        "valuesNo":  [{"axis": "punitive_justice",        "value": 3}],
    },
    "rehabilitative_justice_internet_anonymity": {
        "valuesYes": [{"axis": "rehabilitative_justice", "value": 3}],
        "valuesNo":  [{"axis": "punitive_justice",        "value": 3}],
    },
    "punitive_justice_punishment_goal": {
        "valuesYes": [{"axis": "punitive_justice",        "value": 3}],
        "valuesNo":  [{"axis": "rehabilitative_justice", "value": 3}],
    },
    "punitive_justice_police_armed": {
        "valuesYes": [{"axis": "punitive_justice",        "value": 3}],
        "valuesNo":  [{"axis": "rehabilitative_justice", "value": 3}],
    },
    "punitive_justice_terrorism_protection": {
        "valuesYes": [{"axis": "punitive_justice",        "value": 3}],
        "valuesNo":  [{"axis": "rehabilitative_justice", "value": 3}],
    },
    "punitive_justice_order_authority": {
        "valuesYes": [{"axis": "punitive_justice",        "value": 3}],
        "valuesNo":  [{"axis": "rehabilitative_justice", "value": 3}],
    },
    "punitive_justice_heavy_penalties_efficacy": {
        "valuesYes": [{"axis": "punitive_justice",        "value": 3}],
        "valuesNo":  [{"axis": "rehabilitative_justice", "value": 3}],
    },
    "punitive_justice_preventive_arrest": {
        "valuesYes": [{"axis": "punitive_justice",        "value": 3}],
        "valuesNo":  [{"axis": "rehabilitative_justice", "value": 3}],
    },

    # Revolution / Reform
    "revolution_general_strike_rights": {
        "valuesYes": [{"axis": "revolution", "value": 3}],
        "valuesNo":  [{"axis": "reform",     "value": 3}],
    },
    "revolution_armed_struggle_necessity": {
        "valuesYes": [{"axis": "revolution", "value": 3}],
        "valuesNo":  [{"axis": "reform",     "value": 3}],
    },
    "revolution_insurrection_necessity": {
        "valuesYes": [{"axis": "revolution", "value": 3}],
        "valuesNo":  [{"axis": "reform",     "value": 3}],
    },
    "revolution_political_institutions": {
        "valuesYes": [{"axis": "revolution", "value": 3}],
        "valuesNo":  [{"axis": "reform",     "value": 3}],
    },
    "revolution_election_challenge": {
        "valuesYes": [{"axis": "revolution", "value": 3}],
        "valuesNo":  [{"axis": "reform",     "value": 3}],
    },
    "revolution_hacktivism_political": {
        "valuesYes": [{"axis": "revolution", "value": 3}],
        "valuesNo":  [{"axis": "reform",     "value": 3}],
    },
    "revolution_sabotage_legitimacy": {
        "valuesYes": [{"axis": "revolution", "value": 3}],
        "valuesNo":  [{"axis": "reform",     "value": 3}],
    },
    "reform_lawful_militation": {
        "valuesYes": [{"axis": "reform",     "value": 3}],
        "valuesNo":  [{"axis": "revolution", "value": 3}],
    },
    "reform_revolution_outcome": {
        "valuesYes": [{"axis": "reform",     "value": 3}],
        "valuesNo":  [{"axis": "revolution", "value": 3}],
    },
    "reform_radical_change_impact": {
        "valuesYes": [{"axis": "reform",     "value": 3}],
        "valuesNo":  [{"axis": "revolution", "value": 3}],
    },
    "reform_violence_solution": {
        "valuesYes": [{"axis": "reform",     "value": 3}],
        "valuesNo":  [{"axis": "revolution", "value": 3}],
    },
    "reform_manifestant_violence": {
        "valuesYes": [{"axis": "reform",     "value": 3}],
        "valuesNo":  [{"axis": "revolution", "value": 3}],
    },
    "reform_opposition_compromise": {
        "valuesYes": [{"axis": "reform",     "value": 3}],
        "valuesNo":  [{"axis": "revolution", "value": 3}],
    },
    "reform_individual_lifestyle_change": {
        "valuesYes": [{"axis": "reform",     "value": 3}],
        "valuesNo":  [{"axis": "revolution", "value": 3}],
    },

    # Bonus / Unpaired badges
    "religion_diffusion": {
        "valuesYes": [{"axis": "religion",   "value": 3}],
        "valuesNo":  [],
    },
    "complotism_secret_control": {
        "valuesYes": [{"axis": "complotism", "value": 3}],
        "valuesNo":  [],
    },
    "pragmatism_policy_approach": {
        "valuesYes": [{"axis": "pragmatism", "value": 3}],
        "valuesNo":  [],
    },
    "monarchism_peace_sovereignty": {
        "valuesYes": [{"axis": "monarchism", "value": 3}],
        "valuesNo":  [],
    },
    "veganism_animal_exploitation": {
        "valuesYes": [{"axis": "veganism",   "value": 3}],
        "valuesNo":  [],
    },
    "anarchism_state_abolition": {
        "valuesYes": [{"axis": "anarchism",  "value": 3}],
        "valuesNo":  [],
    },
}


# ---------------------------------------------------------------------------
# Max possible score per axis (for unpaired normalization)
# ---------------------------------------------------------------------------
def _compute_max_scores() -> Dict[str, float]:
    """
    Compute the maximum achievable raw score for each axis.

    For each question, only valuesYes OR valuesNo can fire (not both).
    So for each axis, we take the max contribution from each question.
    """
    max_scores: Dict[str, float] = {}
    for weights in QUESTIONS_WEIGHTS.values():
        # Collect per-axis contributions from yes side and no side separately
        yes_contribs: Dict[str, float] = {}
        no_contribs: Dict[str, float] = {}
        for entry in weights["valuesYes"]:
            yes_contribs[entry["axis"]] = (
                yes_contribs.get(entry["axis"], 0.0) + float(entry["value"])
            )
        for entry in weights["valuesNo"]:
            no_contribs[entry["axis"]] = (
                no_contribs.get(entry["axis"], 0.0) + float(entry["value"])
            )
        # For each axis touched by this question, take whichever side gives more
        all_axes = set(yes_contribs) | set(no_contribs)
        for axis in all_axes:
            best = max(yes_contribs.get(axis, 0.0), no_contribs.get(axis, 0.0))
            max_scores[axis] = max_scores.get(axis, 0.0) + best
    return max_scores


MAX_SCORES = _compute_max_scores()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_scores(answers: Dict[str, str]) -> Dict:
    """
    Compute PolitiScales axis scores from a dict of {question_key: answer_string}.

    Returns:
        {
          "paired": {
            "identity": {"constructivism": 0.87, "essentialism": 0.13},
            ...
          },
          "unpaired": {
            "anarchism": 0.12,
            ...
          },
          "raw": {
            "constructivism": 24.0,
            ...
          }
        }
    """
    raw: Dict[str, float] = {}
    skipped: List[str] = []

    for question_key, answer in answers.items():
        answer_clean = answer.strip().lower()
        if answer_clean not in ANSWER_MULTIPLIERS:
            skipped.append(question_key)
            continue
        yes_mult, no_mult = ANSWER_MULTIPLIERS[answer_clean]

        weights = QUESTIONS_WEIGHTS.get(question_key)
        if weights is None:
            continue

        if yes_mult > 0:
            for entry in weights["valuesYes"]:
                axis = entry["axis"]
                raw[axis] = raw.get(axis, 0.0) + entry["value"] * yes_mult

        if no_mult > 0:
            for entry in weights["valuesNo"]:
                axis = entry["axis"]
                raw[axis] = raw.get(axis, 0.0) + entry["value"] * no_mult

    if skipped:
        logger.warning(
            f"{len(skipped)} answers could not be parsed and were skipped: "
            f"{skipped[:5]}{'…' if len(skipped) > 5 else ''}"
        )

    # --- Paired axes normalization ---
    paired: Dict[str, Dict[str, Optional[float]]] = {}
    for pair_name, (left, right) in PAIRED_AXES.items():
        left_score  = raw.get(left,  0.0)
        right_score = raw.get(right, 0.0)
        total = left_score + right_score
        if total == 0:
            paired[pair_name] = {left: None, right: None}
        else:
            paired[pair_name] = {
                left:  round(left_score  / total, 4),
                right: round(right_score / total, 4),
            }

    # --- Unpaired axes normalization ---
    unpaired: Dict[str, Optional[float]] = {}
    for axis, _threshold in UNPAIRED_AXES.items():
        axis_raw = raw.get(axis, 0.0)
        max_possible = MAX_SCORES.get(axis, 0.0)
        if max_possible == 0:
            unpaired[axis] = None
        else:
            unpaired[axis] = round(axis_raw / max_possible, 4)

    return {
        "paired":   paired,
        "unpaired": unpaired,
        "raw":      {k: round(v, 4) for k, v in raw.items()},
    }


def aggregate_scores(all_scores: List[Dict]) -> Dict:
    """
    Aggregate scores across multiple runs.
    Each element of all_scores is the output of compute_scores().

    Returns per-axis mean, std, and list of values.
    """

    def _stats(values: List[float]) -> Dict:
        n = len(values)
        mean = sum(values) / n
        # Sample standard deviation (n-1) for small N
        variance = (
            sum((v - mean) ** 2 for v in values) / (n - 1)
            if n > 1 else 0.0
        )
        return {
            "mean":   round(mean, 4),
            "std":    round(math.sqrt(variance), 4),
            "values": [round(v, 4) for v in values],
        }

    # Gather all axis names
    paired_keys: Dict[str, Tuple[str, str]] = {}
    for pair_name, pair_axes in PAIRED_AXES.items():
        left, right = pair_axes
        if any(
            all_scores[i]["paired"].get(pair_name, {}).get(left) is not None
            for i in range(len(all_scores))
        ):
            paired_keys[pair_name] = pair_axes

    agg_paired: Dict = {}
    for pair_name, (left, right) in paired_keys.items():
        left_vals  = [s["paired"][pair_name][left]  for s in all_scores if s["paired"][pair_name][left]  is not None]
        right_vals = [s["paired"][pair_name][right] for s in all_scores if s["paired"][pair_name][right] is not None]
        agg_paired[pair_name] = {}
        if left_vals:
            agg_paired[pair_name][left]  = _stats(left_vals)
        if right_vals:
            agg_paired[pair_name][right] = _stats(right_vals)

    agg_unpaired: Dict = {}
    for axis in UNPAIRED_AXES:
        vals = [s["unpaired"][axis] for s in all_scores if s["unpaired"].get(axis) is not None]
        if vals:
            agg_unpaired[axis] = _stats(vals)

    return {
        "runs_count": len(all_scores),
        "paired":     agg_paired,
        "unpaired":   agg_unpaired,
    }
