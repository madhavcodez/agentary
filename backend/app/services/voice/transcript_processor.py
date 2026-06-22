"""Transcript processing: cleanup, analysis, and summarization."""
from __future__ import annotations

import logging
import re
from typing import Any

from ..gemini import generate_text

logger = logging.getLogger(__name__)

# Common ASR filler words and verbal tics to strip
_FILLER_WORDS: set[str] = {
    "um", "uh", "uhh", "umm", "hmm", "hm", "ah", "er", "err",
    "like", "you know", "i mean", "sort of", "kind of", "basically",
    "actually", "literally", "right", "okay so", "so basically",
}

# Patterns that signal key moments in a conversation
_QUESTION_PATTERN = re.compile(
    r"[^.!?]*\?",
    re.IGNORECASE,
)
_OBJECTION_INDICATORS = re.compile(
    r"\b(but|however|unfortunately|can't|cannot|won't|don't think|not sure|"
    r"not interested|no thanks|concern|worried|issue with|problem with)\b",
    re.IGNORECASE,
)
_AGREEMENT_INDICATORS = re.compile(
    r"\b(yes|yeah|sure|absolutely|definitely|sounds good|great|perfect|"
    r"agree|that works|let's do it|i'm in|sign me up|go ahead)\b",
    re.IGNORECASE,
)
_INFO_INDICATORS = re.compile(
    r"\b(my name is|i am|we are|our company|my email|my number|my address|"
    r"located at|phone number|website is|i work at|my role|my title)\b",
    re.IGNORECASE,
)


def process_transcript(
    raw_transcript: str,
    segments: list[dict] | None = None,
) -> dict[str, Any]:
    """Process raw transcript into structured analysis.

    Args:
        raw_transcript: Full transcript text (format: "Speaker: text\\nSpeaker: text")
        segments: Optional list of [{speaker, text, timestamp}] for richer analysis

    Returns:
        Dict with keys: cleaned_transcript, segments, talk_ratio, key_moments, word_count
    """
    if not raw_transcript or not raw_transcript.strip():
        return {
            "cleaned_transcript": "",
            "segments": [],
            "talk_ratio": {},
            "key_moments": [],
            "word_count": 0,
        }

    cleaned = _clean_transcript(raw_transcript)

    parsed_segments = _parse_segments(cleaned, segments)

    talk_ratio = _calculate_talk_ratio(parsed_segments)

    key_moments = _extract_key_moments(cleaned)

    word_count = len(cleaned.split())

    return {
        "cleaned_transcript": cleaned,
        "segments": parsed_segments,
        "talk_ratio": talk_ratio,
        "key_moments": key_moments,
        "word_count": word_count,
    }


async def summarize_call(
    transcript: str,
    context: dict[str, Any] | None = None,
) -> str:
    """Generate a concise summary of the call using Gemini.

    Args:
        transcript: Full transcript text
        context: Optional context (target_name, target_business, extraction_goals)

    Returns:
        2-3 sentence summary of the call
    """
    if not transcript or not transcript.strip():
        return "No transcript available to summarize."

    context_block = ""
    if context:
        parts: list[str] = []
        if target_name := context.get("target_name"):
            parts.append(f"Target contact: {target_name}")
        if target_biz := context.get("target_business"):
            parts.append(f"Business: {target_biz}")
        if goals := context.get("extraction_goals"):
            if isinstance(goals, list):
                parts.append("Extraction goals: " + ", ".join(goals))
            else:
                parts.append(f"Extraction goals: {goals}")
        if parts:
            context_block = "\n\nContext:\n" + "\n".join(f"- {p}" for p in parts)

    prompt = (
        f"Summarize the following phone call transcript in 2-3 concise sentences. "
        f"Focus on the outcome, any commitments made, and next steps. "
        f"Do NOT use bullet points; write in plain prose."
        f"{context_block}\n\n"
        f"Transcript:\n{transcript}"
    )

    system = (
        "You are a concise business call summarizer. "
        "Produce a 2-3 sentence summary covering the call outcome, "
        "key information exchanged, and any agreed-upon next steps. "
        "Write in third person past tense."
    )

    try:
        summary = await generate_text(prompt, system=system, model="gemini-2.5-flash")
        return summary.strip()
    except Exception:
        logger.exception("Failed to generate call summary via Gemini")
        return "Summary generation failed. Please review the transcript manually."


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clean_transcript(text: str) -> str:
    """Remove ASR artifacts: filler words, repeated words, false starts."""
    lines = text.splitlines()
    cleaned_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Preserve "Speaker:" prefix if present
        prefix = ""
        content = stripped
        speaker_match = re.match(r"^([A-Za-z0-9_ ]+):\s*", stripped)
        if speaker_match:
            prefix = speaker_match.group(0)
            content = stripped[len(prefix):]

        content = _remove_filler_words(content)
        content = _remove_repeated_words(content)
        content = _remove_false_starts(content)
        content = _normalize_whitespace(content)

        if content:
            cleaned_lines.append(f"{prefix}{content}")

    return "\n".join(cleaned_lines)


def _remove_filler_words(text: str) -> str:
    """Strip filler words and verbal tics from text."""
    result = text
    # Handle multi-word fillers first (longer patterns before shorter)
    sorted_fillers = sorted(_FILLER_WORDS, key=len, reverse=True)
    for filler in sorted_fillers:
        # Match filler at word boundaries, case-insensitive
        pattern = re.compile(
            r"\b" + re.escape(filler) + r"\b[,.]?\s*",
            re.IGNORECASE,
        )
        result = pattern.sub(" ", result)
    return result.strip()


def _remove_repeated_words(text: str) -> str:
    """Remove immediately repeated words (stuttering artifacts).

    E.g. "the the the meeting" -> "the meeting"
    """
    return re.sub(r"\b(\w+)(?:\s+\1)+\b", r"\1", text, flags=re.IGNORECASE)


def _remove_false_starts(text: str) -> str:
    """Remove false starts indicated by a dash mid-sentence.

    E.g. "I was go- I was going to say" -> "I was going to say"
    """
    # Remove word fragments ending with a hyphen (e.g. "go-")
    result = re.sub(r"\b\w+- ", "", text)
    return result


def _normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces, fix spacing around punctuation."""
    text = re.sub(r"\s{2,}", " ", text)
    # Remove space before punctuation
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    # Ensure space after punctuation (except at end)
    text = re.sub(r"([.,!?;:])(?=[A-Za-z])", r"\1 ", text)
    return text.strip()


def _parse_segments(
    cleaned_transcript: str,
    raw_segments: list[dict] | None = None,
) -> list[dict]:
    """Build a list of segment dicts from transcript lines or raw segments.

    Each segment: {speaker: str, text: str, timestamp: float | None, word_count: int}
    """
    if raw_segments:
        return [
            {
                "speaker": seg.get("speaker", "Unknown"),
                "text": seg.get("text", ""),
                "timestamp": seg.get("timestamp"),
                "word_count": len(seg.get("text", "").split()),
            }
            for seg in raw_segments
        ]

    segments: list[dict] = []
    for line in cleaned_transcript.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^([A-Za-z0-9_ ]+):\s*(.*)", stripped)
        if match:
            speaker = match.group(1).strip()
            text = match.group(2).strip()
        else:
            speaker = "Unknown"
            text = stripped
        segments.append({
            "speaker": speaker,
            "text": text,
            "timestamp": None,
            "word_count": len(text.split()),
        })
    return segments


def _calculate_talk_ratio(segments: list[dict]) -> dict[str, float]:
    """Calculate the ratio of speaking for each participant.

    Returns a dict mapping speaker names to their share of total words (0.0-1.0).
    Also includes an 'agent_ratio' key if an Agent/Assistant speaker is detected,
    and a 'user_ratio' key for the other party.
    """
    if not segments:
        return {}

    word_counts: dict[str, int] = {}
    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        words = seg.get("word_count", len(seg.get("text", "").split()))
        word_counts[speaker] = word_counts.get(speaker, 0) + words

    total = sum(word_counts.values())
    if total == 0:
        return dict.fromkeys(word_counts, 0.0)

    ratios: dict[str, float] = {
        speaker: round(count / total, 4)
        for speaker, count in word_counts.items()
    }

    # Try to identify agent vs user speakers
    agent_keywords = {"agent", "assistant", "ai", "bot", "rep", "representative"}
    user_keywords = {"user", "customer", "caller", "client", "contact"}

    agent_speakers: list[str] = []
    user_speakers: list[str] = []

    for speaker in word_counts:
        lower = speaker.lower()
        if any(kw in lower for kw in agent_keywords):
            agent_speakers.append(speaker)
        elif any(kw in lower for kw in user_keywords):
            user_speakers.append(speaker)

    # If exactly two speakers and none matched keywords, assume first is agent
    if not agent_speakers and not user_speakers and len(word_counts) == 2:
        speakers_list = list(word_counts.keys())
        agent_speakers = [speakers_list[0]]
        user_speakers = [speakers_list[1]]

    if agent_speakers:
        ratios["agent_ratio"] = round(
            sum(word_counts[s] for s in agent_speakers) / total, 4,
        )
    if user_speakers:
        ratios["user_ratio"] = round(
            sum(word_counts[s] for s in user_speakers) / total, 4,
        )

    return ratios


def _extract_key_moments(transcript: str) -> list[dict]:
    """Identify key moments: questions, answers, objections, agreements.

    Returns a list of dicts: {type, speaker, text, line_number}
    """
    moments: list[dict] = []
    lines = transcript.splitlines()

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue

        # Parse speaker
        speaker = "Unknown"
        content = stripped
        speaker_match = re.match(r"^([A-Za-z0-9_ ]+):\s*(.*)", stripped)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            content = speaker_match.group(2).strip()

        if not content:
            continue

        # Check for questions
        if _QUESTION_PATTERN.search(content):
            moments.append({
                "type": "question",
                "speaker": speaker,
                "text": content,
                "line_number": line_num,
            })

        # Check for objections
        if _OBJECTION_INDICATORS.search(content):
            # Avoid false positives: require minimum length for objection detection
            if len(content.split()) >= 4:
                moments.append({
                    "type": "objection",
                    "speaker": speaker,
                    "text": content,
                    "line_number": line_num,
                })

        # Check for agreements
        if _AGREEMENT_INDICATORS.search(content):
            moments.append({
                "type": "agreement",
                "speaker": speaker,
                "text": content,
                "line_number": line_num,
            })

        # Check for information exchange
        if _INFO_INDICATORS.search(content):
            moments.append({
                "type": "information",
                "speaker": speaker,
                "text": content,
                "line_number": line_num,
            })

    # Deduplicate: if a line triggers both question and objection, keep both
    # but remove exact duplicates (same type + same line_number)
    seen: set[tuple[str, int]] = set()
    unique_moments: list[dict] = []
    for moment in moments:
        key = (moment["type"], moment["line_number"])
        if key not in seen:
            seen.add(key)
            unique_moments.append(moment)

    return unique_moments
