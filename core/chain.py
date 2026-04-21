"""
core/chain.py
─────────────
Builds two LangChain LCEL chains:

1. screening_chain  — RunnableWithMessageHistory wrapping the main
                      conversational prompt + LLM + parser.
                      Memory is managed by MemoryManager.

2. extract_candidate_info() — a one-shot extraction call that parses
                               structured JSON from conversation text.
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory

from core.llm import get_llm
from core.memory import memory_manager
from core.prompts import SCREENING_PROMPT, EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


# ── Screening chain ───────────────────────────────────────────────────────────

def build_screening_chain() -> RunnableWithMessageHistory:
    """
    Build the main conversational chain with persistent message history.

    Chain: ScreeningPrompt → ChatHuggingFace → StrOutputParser
    Wrapped in RunnableWithMessageHistory so conversation context is
    automatically injected on every call.
    """
    llm = get_llm()
    base_chain = SCREENING_PROMPT | llm | StrOutputParser()

    chain = RunnableWithMessageHistory(
        base_chain,
        get_session_history=memory_manager.get_history,
        input_messages_key="input",
        history_messages_key="history",
    )
    logger.info("Screening chain built")
    return chain


# ── Extraction chain ──────────────────────────────────────────────────────────

def extract_candidate_info(
    conversation_text: str,
    window: int = 20,
) -> dict:
    """
    Parse structured candidate profile fields out of a conversation.

    Uses a dedicated prompt that asks the LLM to return only JSON.
    Falls back to an empty dict on parse failure — callers must handle
    missing keys gracefully.
    """
    llm = get_llm()
    extraction_chain = EXTRACTION_PROMPT | llm | StrOutputParser()

    try:
        raw: str = extraction_chain.invoke({
            "conversation": conversation_text,
            "window": window,
        })
    except Exception as exc:
        logger.error("Extraction LLM call failed: %s", exc)
        return {}

    # Strip markdown code fences if the model added them
    clean = re.sub(r"```(?:json)?|```", "", raw, flags=re.IGNORECASE).strip()

    # Sometimes models emit text before/after the JSON — find the first { }
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if not match:
        logger.warning("No JSON object found in extraction output: %r", raw[:300])
        return {}

    try:
        result = json.loads(match.group())
        logger.debug("Extracted fields: %s", list(result.keys()))
        return result
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error in extraction: %s | raw=%r", exc, raw[:300])
        return {}
