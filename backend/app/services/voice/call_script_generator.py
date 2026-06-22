"""AI-powered call script generation for voice extraction sessions."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..gemini import generate_structured

logger = logging.getLogger(__name__)

_SCRIPT_SCHEMA = """{
  "opener": "string — opening line for the call",
  "questions": [{"field": "string", "primary_question": "string", "follow_up": "string", "probes": ["string"]}],
  "objection_handlers": {"busy": "string", "not_interested": "string", "who_are_you": "string"},
  "closing": "string — how to end the call",
  "voicemail_script": "string — message if voicemail"
}"""

_SESSION_TYPE_GUIDANCE: dict[str, str] = {
    "research_extraction": (
        "You are conducting research to gather specific data points. "
        "Be professional and curious. Frame questions as genuine interest "
        "in learning about their business or expertise. Avoid sounding "
        "like a telemarketer."
    ),
    "screening": (
        "You are conducting a preliminary screening call. Be warm but "
        "efficient. Explain the purpose upfront and move through "
        "qualification criteria methodically."
    ),
    "survey": (
        "You are conducting a brief survey. Be respectful of their time, "
        "explain how long it will take, and make questions feel "
        "conversational rather than formulaic."
    ),
    "custom": (
        "Adapt your approach to the specific goals outlined. Be natural "
        "and conversational while ensuring all extraction goals are met."
    ),
}

_DEFAULT_PERSONA: dict[str, str] = {
    "name": "Alex",
    "role": "Research Associate",
    "tone": "friendly and professional",
    "style": "conversational",
}


def _build_persona_description(persona: dict[str, Any]) -> str:
    """Build a human-readable persona description from config."""
    name = persona.get("name", _DEFAULT_PERSONA["name"])
    role = persona.get("role", _DEFAULT_PERSONA["role"])
    tone = persona.get("tone", _DEFAULT_PERSONA["tone"])
    style = persona.get("style", _DEFAULT_PERSONA["style"])
    return (
        f"Your name is {name}. You are a {role}. "
        f"Your tone is {tone} and your communication style is {style}."
    )


def _format_extraction_goals(goals: list[dict[str, Any]]) -> str:
    """Format extraction goals into a readable prompt section."""
    if not goals:
        return "No specific extraction goals defined. Have a general conversation."

    lines: list[str] = []
    for i, goal in enumerate(goals, 1):
        field = goal.get("field", "unknown")
        question = goal.get("question", "")
        field_type = goal.get("type", "text")
        required = goal.get("required", False)
        priority = "REQUIRED" if required else "optional"
        lines.append(
            f"  {i}. [{priority}] {field} ({field_type}): {question}"
        )
    return "\n".join(lines)


def _format_context(context: dict[str, Any] | None) -> str:
    """Format target context into a readable prompt section."""
    if not context:
        return "No additional context available."

    lines: list[str] = []
    for key, value in context.items():
        if isinstance(value, (list, dict)):
            value = json.dumps(value, indent=2)
        lines.append(f"  - {key}: {value}")
    return "\n".join(lines)


async def generate_script(session_data: dict[str, Any]) -> dict[str, Any]:
    """Generate a complete call script for a voice session.

    Args:
        session_data: Dict with target_name, target_business, target_context,
                     extraction_goals, persona_config, session_type

    Returns:
        Dict with opener, questions, objection_handlers, closing, voicemail_script
    """
    target_name = session_data.get("target_name", "the contact")
    target_business = session_data.get("target_business", "")
    target_context = session_data.get("target_context") or {}
    extraction_goals = session_data.get("extraction_goals") or []
    persona = session_data.get("persona_config") or dict(_DEFAULT_PERSONA)
    session_type = session_data.get("session_type", "research_extraction")

    type_guidance = _SESSION_TYPE_GUIDANCE.get(
        session_type, _SESSION_TYPE_GUIDANCE["custom"]
    )
    persona_desc = _build_persona_description(persona)
    goals_text = _format_extraction_goals(extraction_goals)
    context_text = _format_context(target_context)

    business_clause = (
        f" at {target_business}" if target_business else ""
    )

    prompt = f"""Generate a natural, conversational call script for an outbound phone call.

CALLER PERSONA:
{persona_desc}

CALL TYPE: {session_type}
TYPE GUIDANCE: {type_guidance}

TARGET:
  Name: {target_name}
  Business: {target_business or "Not specified"}
  Known context:
{context_text}

INFORMATION TO EXTRACT:
{goals_text}

REQUIREMENTS:
1. The opener should introduce yourself naturally, reference {target_name}{business_clause} \
by name, and give a brief, honest reason for the call. Keep it under 3 sentences.
2. For each extraction goal, provide:
   - A "primary_question" that sounds conversational, not interrogative
   - A "follow_up" for when the initial answer is vague or incomplete
   - 2-3 "probes" — short nudges to go deeper (e.g., "Could you say more about that?")
   - The "field" name matching the extraction goal exactly
3. Objection handlers should be empathetic and non-pushy:
   - "busy": Acknowledge their time, offer to call back, keep it to 15 seconds
   - "not_interested": Respect their decision, leave the door open
   - "who_are_you": Re-introduce clearly with name and purpose
4. The closing should thank them, confirm any follow-up actions, and end warmly.
5. The voicemail_script should be 20-30 seconds: introduce yourself, state purpose, \
leave a callback number, and sound friendly.

Generate the script as JSON matching the provided schema. Make every line sound like \
something a real person would say — no corporate jargon, no robotic phrasing."""

    logger.info(
        "Generating call script for target=%s business=%s type=%s",
        target_name,
        target_business,
        session_type,
    )

    script = await generate_structured(prompt, schema_hint=_SCRIPT_SCHEMA)

    # Validate required top-level keys and fill defaults for any missing ones
    validated: dict[str, Any] = {
        "opener": script.get("opener", f"Hi, is this {target_name}? "),
        "questions": script.get("questions", []),
        "objection_handlers": {
            "busy": "I totally understand you're busy — would there be a better time for a quick 2-minute chat?",
            "not_interested": "No worries at all, I appreciate your time. Have a great day!",
            "who_are_you": (
                f"Of course! My name is {persona.get('name', 'Alex')}, "
                f"I'm a {persona.get('role', 'researcher')}. "
                "I'm reaching out because I had a quick question."
            ),
            **(script.get("objection_handlers") or {}),
        },
        "closing": script.get(
            "closing",
            "Thank you so much for your time — I really appreciate it. Have a wonderful day!",
        ),
        "voicemail_script": script.get(
            "voicemail_script",
            (
                f"Hi {target_name}, this is {persona.get('name', 'Alex')}. "
                "I was hoping to chat briefly — no rush at all. "
                "Feel free to give me a call back when you get a chance. "
                "Thanks, and have a great day!"
            ),
        ),
    }

    # Ensure every extraction goal has a corresponding question entry
    covered_fields = {q.get("field") for q in validated["questions"]}
    for goal in extraction_goals:
        field = goal.get("field", "")
        if field and field not in covered_fields:
            validated["questions"].append(
                {
                    "field": field,
                    "primary_question": goal.get("question", f"Could you tell me about {field}?"),
                    "follow_up": f"Just to make sure I understand — could you elaborate on {field}?",
                    "probes": [
                        "Could you say more about that?",
                        "And how does that typically work?",
                    ],
                }
            )

    logger.info(
        "Script generated: %d questions, target=%s",
        len(validated["questions"]),
        target_name,
    )
    return validated


async def build_system_prompt(
    session_data: dict[str, Any], script: dict[str, Any]
) -> str:
    """Build a dynamic system prompt for Gemini Live during the call.

    Combines persona, target context, extraction goals, and the generated
    script into a comprehensive system prompt.

    Args:
        session_data: Session configuration data
        script: Generated call script from generate_script()

    Returns:
        Complete system prompt string for Gemini Live
    """
    target_name = session_data.get("target_name", "the contact")
    target_business = session_data.get("target_business", "")
    target_context = session_data.get("target_context") or {}
    extraction_goals = session_data.get("extraction_goals") or []
    persona = session_data.get("persona_config") or dict(_DEFAULT_PERSONA)
    session_type = session_data.get("session_type", "research_extraction")

    persona_desc = _build_persona_description(persona)
    type_guidance = _SESSION_TYPE_GUIDANCE.get(
        session_type, _SESSION_TYPE_GUIDANCE["custom"]
    )
    context_text = _format_context(target_context)
    goals_text = _format_extraction_goals(extraction_goals)

    # Build required-fields list for the extraction checklist
    required_fields = [
        g.get("field", "unknown")
        for g in extraction_goals
        if g.get("required", False)
    ]
    optional_fields = [
        g.get("field", "unknown")
        for g in extraction_goals
        if not g.get("required", False)
    ]

    questions_block = _format_questions_for_prompt(script.get("questions", []))
    objections_block = _format_objections_for_prompt(
        script.get("objection_handlers", {})
    )

    prompt = f"""You are conducting a live outbound phone call. You must speak naturally, \
listen actively, and adapt in real time. Everything below is your preparation — use it \
as a guide, not a rigid script.

═══════════════════════════════════════════
IDENTITY & PERSONA
═══════════════════════════════════════════
{persona_desc}
You are calling {target_name}{f' at {target_business}' if target_business else ''}.
Call type: {session_type}

═══════════════════════════════════════════
VOICE & DELIVERY RULES
═══════════════════════════════════════════
- Speak at a natural pace — not too fast, not too slow.
- Use conversational fillers sparingly ("Sure", "Got it", "That makes sense").
- Mirror the other person's energy: if they are brief, be concise; if chatty, engage.
- Never read questions verbatim — paraphrase based on the flow.
- Pause after asking a question; give them time to answer.
- If they go off-topic, gently steer back without being abrupt.
- Use their name occasionally to keep the conversation personal.
- {type_guidance}

═══════════════════════════════════════════
WHAT YOU KNOW ABOUT THE TARGET
═══════════════════════════════════════════
{context_text}

Use this context to personalize the conversation and demonstrate you have done your \
homework, but do NOT reveal that you are an AI or that you have a dossier. Weave \
context in naturally (e.g., "I saw your business does X — that's really interesting").

═══════════════════════════════════════════
OPENING THE CALL
═══════════════════════════════════════════
{script.get('opener', f'Hi, is this {target_name}?')}

If they say "yes", continue with a warm transition into the purpose.
If they say "no" or "wrong number", apologize politely and end the call.
If it goes to voicemail, leave this message:
{script.get('voicemail_script', 'Hi, this is a quick call — I will try again later.')}

═══════════════════════════════════════════
INFORMATION TO GATHER (YOUR MISSION)
═══════════════════════════════════════════
You need to extract the following data points during the conversation.
Do NOT ask them as a checklist — weave them naturally into the dialogue.

{goals_text}

Required fields (must obtain): {', '.join(required_fields) if required_fields else 'None'}
Optional fields (nice to have): {', '.join(optional_fields) if optional_fields else 'None'}

═══════════════════════════════════════════
QUESTION GUIDE
═══════════════════════════════════════════
Use these as inspiration, not exact wording. Adapt based on what they say.

{questions_block}

═══════════════════════════════════════════
HANDLING OBJECTIONS
═══════════════════════════════════════════
{objections_block}

Additional objection principles:
- Never argue or push back aggressively.
- Acknowledge their concern first, then respond.
- If they firmly decline, thank them and end gracefully.
- If they ask to be removed from a list, agree immediately and apologize.

═══════════════════════════════════════════
CLOSING THE CALL
═══════════════════════════════════════════
{script.get('closing', 'Thank you for your time — I really appreciate it!')}

Before hanging up:
- Briefly summarize what you learned (confirms accuracy).
- Ask if there is anything they would like to add.
- Thank them sincerely.

═══════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════
1. You are a REAL PERSON on a phone call. Never break character.
2. Never say "As an AI" or reference being artificial in any way.
3. If asked directly "Are you a robot?", deflect naturally: \
"Ha, no — just calling from my desk. Sometimes the phone connection \
makes it sound a bit off!"
4. Keep the call under 5 minutes unless they are engaged and willing.
5. If you sense frustration or impatience, offer to wrap up.
6. Never fabricate information about yourself or your organization.
7. Stay warm and human throughout. Your goal is a pleasant, productive conversation.
8. Track which extraction goals you have covered. Try to cover all required \
fields before closing.
9. If the conversation naturally provides an answer to one of your goals, \
acknowledge it and mark it mentally — do not re-ask."""

    logger.info(
        "System prompt built: %d chars, target=%s, %d goals",
        len(prompt),
        target_name,
        len(extraction_goals),
    )
    return prompt


def _format_questions_for_prompt(questions: list[dict[str, Any]]) -> str:
    """Format script questions into a readable block for the system prompt."""
    if not questions:
        return "No pre-generated questions. Use the extraction goals above to guide your questions."

    lines: list[str] = []
    for i, q in enumerate(questions, 1):
        field = q.get("field", "unknown")
        primary = q.get("primary_question", "")
        follow_up = q.get("follow_up", "")
        probes = q.get("probes", [])

        lines.append(f"{i}. [{field}]")
        lines.append(f"   Ask: \"{primary}\"")
        if follow_up:
            lines.append(f"   If vague: \"{follow_up}\"")
        if probes:
            probes_text = " / ".join(f"\"{p}\"" for p in probes)
            lines.append(f"   Dig deeper: {probes_text}")
        lines.append("")
    return "\n".join(lines)


def _format_objections_for_prompt(handlers: dict[str, str]) -> str:
    """Format objection handlers into a readable block for the system prompt."""
    if not handlers:
        return "No specific objection scripts. Use empathy and respect their decision."

    label_map = {
        "busy": "If they say they are busy",
        "not_interested": "If they are not interested",
        "who_are_you": "If they ask who you are",
    }

    lines: list[str] = []
    for key, response in handlers.items():
        label = label_map.get(key, f"If they say \"{key}\"")
        lines.append(f"- {label}: \"{response}\"")
    return "\n".join(lines)
