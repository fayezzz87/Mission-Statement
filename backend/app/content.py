"""Shared assignment content: the scenario shown to students and used in
every AI prompt, and the 5 required mission-statement characteristics."""

SCENARIO = {
    "company": "Slice Co.",
    "market_landscape": (
        "The US pizza market is dominated by a few large players with distinct "
        "positioning — delivery speed and convenience (Domino's-style), "
        "ingredient quality and “better ingredients” messaging (Papa John's-style), "
        "value/price leadership (Little Caesars-style), and dine-in/family experience "
        "(Pizza Hut-style, historically). Independent and regional chains often compete "
        "on local/artisanal positioning instead."
    ),
    "company_facts": [
        "New entrant, US-only for now",
        "No established brand recognition",
        "Moderate funding",
        "Planning both delivery and carry-out",
    ],
}

# Fixed order/wording matters: the evaluator tool schema references these by index (c1..c5).
CHARACTERISTICS = [
    "Focuses on a limited number of specific goals",
    "Stresses the company's major policies and values",
    "Defines the major market(s) the company aims to serve",
    "Takes a long-term view",
    "Short, memorable, and meaningful",
]

WORD_COUNT_GUIDELINE = 20


def scenario_prompt_block():
    facts = "\n".join(f"- {f}" for f in SCENARIO["company_facts"])
    return f"""COMPANY: {SCENARIO['company']}, a fictional company entering the US pizza market.

MARKET LANDSCAPE: {SCENARIO['market_landscape']}

COMPANY FACTS:
{facts}"""
