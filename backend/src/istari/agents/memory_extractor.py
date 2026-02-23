"""Post-turn memory extraction — fire-and-forget async task.

After each agent response, extract memorable facts and store them in the
Memory table. This is what makes Istari learn from conversations over time.
"""

import json
import logging

from istari.llm.router import completion
from istari.tools.memory.store import MemoryStore

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """\
Given a single conversation exchange, identify facts about the user worth remembering long-term.

WORTH remembering:
- Personal details (name, role, location, family)
- Ongoing projects or goals they mentioned
- Preferences or dislikes they expressed
- Recurring commitments or habits
- Important context about their work or life

NOT worth remembering:
- One-off task requests ("add a todo", "mark as done")
- Questions about today's schedule or transient information
- Things already obvious from context

Output a JSON array of concise fact strings. Empty array [] if nothing is memorable.
No preamble, no explanation — only the JSON array.

User: {user_message}
Assistant: {assistant_response}
"""


async def extract_and_store(
    user_message: str,
    assistant_response: str,
    session_factory,
) -> None:
    """Extract memorable facts from a turn and persist any novel ones."""
    prompt = _EXTRACT_PROMPT.format(
        user_message=user_message[:500],
        assistant_response=assistant_response[:500],
    )

    try:
        result = await completion(
            "memory_extraction",
            [{"role": "user", "content": prompt}],
        )
        raw = (result.choices[0].message.content or "[]").strip()
    except Exception:
        logger.exception("Memory extraction LLM call failed")
        return

    # Strip markdown fences if present
    if "```" in raw:
        raw = raw.split("```")[1].lstrip("json").strip()

    try:
        facts = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Memory extraction: could not parse JSON — %r", raw[:200])
        return

    if not isinstance(facts, list):
        return

    facts = [f.strip() for f in facts if isinstance(f, str) and f.strip()]
    if not facts:
        return

    try:
        async with session_factory() as session:
            store = MemoryStore(session)
            existing = await store.list_explicit()
            existing_lower = {m.content.lower() for m in existing}

            stored = 0
            for fact in facts:
                if fact.lower() not in existing_lower:
                    await store.store(fact, source="auto")
                    stored += 1

            if stored:
                await session.commit()
                logger.info("Memory extraction | stored %d new fact(s)", stored)
    except Exception:
        logger.exception("Memory extraction store failed")
