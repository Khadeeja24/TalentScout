"""
core/llm.py
───────────
Initialise the HuggingFace Inference API LLM via LangChain.

Model  : mistralai/Mistral-7B-Instruct-v0.2  (default, set HF_MODEL_ID to override)
Provider: "hf-inference" — HuggingFace's own hosted inference endpoints.
           This is explicit to avoid the library auto-selecting an unsupported
           third-party provider (e.g. featherless-ai) as the default.

Wrapper: HuggingFaceEndpoint → ChatHuggingFace
         ChatHuggingFace applies the model's native chat template automatically
         (Mistral [INST] tokens, Llama <|begin_of_text|>, etc.).
"""

from __future__ import annotations

import logging

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace

from config.settings import settings

logger = logging.getLogger(__name__)

# Module-level singletons (lazy-initialised)
_endpoint: HuggingFaceEndpoint | None = None
_chat_model: ChatHuggingFace | None = None


def get_llm() -> ChatHuggingFace:
    """
    Return a cached ChatHuggingFace instance.
    Thread-safe: the module-level singleton is shared across Streamlit re-runs
    within the same process, so the model is only loaded once.
    """
    global _endpoint, _chat_model

    if _chat_model is None:
        logger.info(
            "Initialising HuggingFace LLM → %s (provider: %s)",
            settings.HF_MODEL_ID,
            settings.HF_PROVIDER,
        )

        _endpoint = HuggingFaceEndpoint(
            repo_id=settings.HF_MODEL_ID,
            task="text-generation",
            provider=settings.HF_PROVIDER,          # explicit — avoids unsupported provider error
            max_new_tokens=settings.MAX_NEW_TOKENS,
            temperature=settings.TEMPERATURE,
            repetition_penalty=settings.REPETITION_PENALTY,
            huggingfacehub_api_token=settings.HF_API_TOKEN,
            do_sample=True,
            return_full_text=False,
        )

        _chat_model = ChatHuggingFace(
            llm=_endpoint,
            verbose=False,
        )

        logger.info("LLM ready.")

    return _chat_model