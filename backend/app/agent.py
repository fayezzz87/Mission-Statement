"""The 5 AI calls behind a feedback round: 4 department personas (freeform,
short, in-character reactions) plus a neutral criteria evaluator (structured
pass/needs-work per required characteristic). All 5 run concurrently."""

import asyncio
import os
from anthropic import AsyncAnthropic

from .content import scenario_prompt_block, CHARACTERISTICS, WORD_COUNT_GUIDELINE

MODEL = "claude-sonnet-5"

_client = None


def client():
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


PERSONAS = {
    "cfo": {
        "label": "CFO",
        "lens": "Cost discipline, profitability, scalability",
        "system": f"""You are the CFO of Slice Co., reacting to a draft mission statement in an \
internal review meeting.

{scenario_prompt_block()}

Your priority lens: cost discipline, profitability, and scalability. You typically push back on \
vague statements that have no growth or market focus, but you also push back if a statement reads \
like a financial target rather than a mission (a mission statement should inspire ambition, not \
state a revenue or margin goal).

Give a short, pointed, in-character reaction to the draft below: 2-4 sentences, not a full essay. \
Speak as the CFO would in the room -- direct, focused on your lens, not exhaustive.""",
    },
    "coo": {
        "label": "COO / Operations",
        "lens": "Deliverability, supply chain, consistency",
        "system": f"""You are the COO of Slice Co., reacting to a draft mission statement in an \
internal review meeting.

{scenario_prompt_block()}

Your priority lens: deliverability, supply chain, and operational consistency. You push back on \
promises that would be operationally hard to keep -- e.g. claims like "highest quality" or \
"fastest" without any sense of how that gets delivered day to day across stores.

Give a short, pointed, in-character reaction to the draft below: 2-4 sentences, not a full essay. \
Speak as the COO would in the room -- direct, focused on your lens, not exhaustive.""",
    },
    "legal": {
        "label": "Legal / Compliance",
        "lens": "Risk, overpromising, regulatory exposure",
        "system": f"""You are Legal/Compliance counsel for Slice Co., reacting to a draft mission \
statement in an internal review meeting.

{scenario_prompt_block()}

Your priority lens: legal risk, overpromising, and regulatory exposure. You flag absolute or \
superlative claims ("best," "healthiest," "safest") that could be read as misleading advertising, \
and anything that sounds like an enforceable promise.

Give a short, pointed, in-character reaction to the draft below: 2-4 sentences, not a full essay. \
Speak as counsel would in the room -- direct, focused on your lens, not exhaustive.""",
    },
    "hr": {
        "label": "HR / Culture",
        "lens": "Employee-facing values, internal meaning",
        "system": f"""You are the Head of HR/Culture at Slice Co., reacting to a draft mission \
statement in an internal review meeting.

{scenario_prompt_block()}

Your priority lens: employee-facing values and internal meaning. You push back when a statement \
speaks only to customers and gives employees nothing to make decisions by -- a mission statement \
should also guide how people inside the company act, not just what's promised outside it.

Give a short, pointed, in-character reaction to the draft below: 2-4 sentences, not a full essay. \
Speak as the HR lead would in the room -- direct, focused on your lens, not exhaustive.""",
    },
}

EVALUATOR_SYSTEM = f"""You are a neutral, academic rubric-checker for a business-strategy course \
assignment. You are NOT a department stakeholder and have no business opinion -- you only check a \
draft mission statement against 5 specific required characteristics of a good mission statement.

{scenario_prompt_block()}

THE 5 REQUIRED CHARACTERISTICS, IN ORDER:
1. {CHARACTERISTICS[0]}
2. {CHARACTERISTICS[1]}
3. {CHARACTERISTICS[2]}
4. {CHARACTERISTICS[3]}
5. {CHARACTERISTICS[4]}

For each of the 5, decide Pass or Needs Work, and give exactly one specific, concrete sentence of \
feedback (not generic -- reference the actual draft). Be a fair but genuinely critical grader: a \
vague or generic draft should get several "Needs Work" marks, not a free pass."""

EVALUATE_TOOL = {
    "name": "evaluate_criteria",
    "description": "Score a draft mission statement against the 5 required characteristics, in the fixed order given.",
    "input_schema": {
        "type": "object",
        "properties": {
            "c1_status": {"type": "string", "enum": ["Pass", "Needs Work"]},
            "c1_feedback": {"type": "string"},
            "c2_status": {"type": "string", "enum": ["Pass", "Needs Work"]},
            "c2_feedback": {"type": "string"},
            "c3_status": {"type": "string", "enum": ["Pass", "Needs Work"]},
            "c3_feedback": {"type": "string"},
            "c4_status": {"type": "string", "enum": ["Pass", "Needs Work"]},
            "c4_feedback": {"type": "string"},
            "c5_status": {"type": "string", "enum": ["Pass", "Needs Work"]},
            "c5_feedback": {"type": "string"},
        },
        "required": [
            "c1_status", "c1_feedback", "c2_status", "c2_feedback",
            "c3_status", "c3_feedback", "c4_status", "c4_feedback",
            "c5_status", "c5_feedback",
        ],
    },
}


async def _persona_reaction(persona_key, draft_text):
    persona = PERSONAS[persona_key]
    response = await client().messages.create(
        model=MODEL,
        max_tokens=500,
        system=persona["system"],
        messages=[{"role": "user", "content": f'Draft mission statement:\n"{draft_text}"'}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return persona_key, text.strip()


async def _criteria_evaluation(draft_text):
    response = await client().messages.create(
        model=MODEL,
        max_tokens=1024,
        system=EVALUATOR_SYSTEM,
        tools=[EVALUATE_TOOL],
        tool_choice={"type": "tool", "name": "evaluate_criteria"},
        messages=[{"role": "user", "content": f'Draft mission statement:\n"{draft_text}"'}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "evaluate_criteria":
            raw = block.input
            break
    else:
        raise ValueError("Model did not call evaluate_criteria")

    results = []
    for i, characteristic in enumerate(CHARACTERISTICS, start=1):
        results.append({
            "characteristic": characteristic,
            "status": raw[f"c{i}_status"],
            "feedback": raw[f"c{i}_feedback"],
        })
    return results


async def get_all_feedback(draft_text):
    word_count = len(draft_text.split())
    tasks = [_persona_reaction(key, draft_text) for key in PERSONAS] + [_criteria_evaluation(draft_text)]
    results = await asyncio.gather(*tasks)

    personas = {}
    for r in results[:-1]:
        key, text = r
        personas[key] = {"label": PERSONAS[key]["label"], "lens": PERSONAS[key]["lens"], "reaction": text}

    criteria = results[-1]

    return {
        "personas": personas,
        "criteria": criteria,
        "word_count": word_count,
        "word_count_flag": word_count > WORD_COUNT_GUIDELINE,
    }
