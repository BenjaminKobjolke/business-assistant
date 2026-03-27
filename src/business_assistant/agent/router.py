"""AI-based category router — selects plugin categories for each message."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage

from business_assistant.config.constants import ROUTER_KEYWORD_HINTS, ROUTER_SYSTEM_PROMPT
from business_assistant.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class CategorySelection(BaseModel):
    """Structured output from the router agent."""

    categories: list[str]


@dataclass(frozen=True)
class RoutingResult:
    """Result of category routing."""

    categories: set[str]
    usage: RunUsage | None
    failed: bool = False


class CategoryRouter:
    """Uses a lightweight AI model to select which plugin categories are needed."""

    def __init__(
        self, registry: PluginRegistry, model: Any,
        model_name: str = "", retries: int = 1,
        provider: str = "",
    ) -> None:
        self._registry = registry
        self._model_name = model_name or (model if isinstance(model, str) else str(model))
        self._all_categories = registry.all_categories()
        self._system_prompt = self._build_prompt()
        self._text_mode = provider == "ollama"
        if self._text_mode:
            self._agent: Agent = Agent(
                model,
                system_prompt=self._system_prompt,
                output_type=str,
            )
        else:
            self._agent = Agent(
                model,
                system_prompt=self._system_prompt,
                output_type=CategorySelection,
                retries=retries,
            )

    @property
    def model_name(self) -> str:
        """Return the model name used for routing."""
        return self._model_name

    def route(self, text: str) -> RoutingResult:
        """Select plugin categories needed for a user message.

        Returns selected categories (filtered to registered ones,
        expanded with dependencies) and usage data for tracking.
        Falls back to all categories on error.
        """
        try:
            result = self._agent.run_sync(text)
            if self._text_mode:
                raw_categories = set(self._parse_categories(result.output))
            else:
                raw_categories = set(result.output.categories)

            # Filter to only registered categories
            valid = raw_categories & self._all_categories
            # Boost with keyword-based hints
            keyword_cats = self._apply_keyword_hints(text)
            if keyword_cats - valid:
                logger.info(
                    "Keyword hints boosted categories: %s", keyword_cats - valid,
                )
            valid |= keyword_cats
            # Expand with required_categories dependencies
            valid = self._expand_dependencies(valid)

            logger.info(
                "Router selected categories: %s (raw: %s)",
                valid, raw_categories,
            )
            return RoutingResult(categories=valid, usage=result.usage())
        except Exception:
            logger.warning("Router failed", exc_info=True)
            return RoutingResult(
                categories=set(),
                usage=RunUsage(requests=1),
                failed=True,
            )

    @staticmethod
    def _parse_categories(text: str) -> list[str]:
        """Parse category list from model text response.

        Handles JSON arrays like '["email", "calendar"]' and also
        extracts arrays embedded in markdown or extra text.
        """
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.startswith("json"):
                text = text[4:].strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (json.JSONDecodeError, ValueError):
            pass
        # Fallback: try to find a JSON array in the text
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end > start:
            try:
                parsed = json.loads(text[start:end + 1])
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except (json.JSONDecodeError, ValueError):
                pass
        return []

    def _apply_keyword_hints(self, text: str) -> set[str]:
        """Detect categories from keywords in the input text.

        Supplements the AI router by matching words against
        ROUTER_KEYWORD_HINTS, filtered to registered categories.
        """
        tokens = set(re.findall(r"[a-zA-ZäöüÄÖÜß-]+", text.lower()))
        hints: set[str] = set()
        for token in tokens:
            category = ROUTER_KEYWORD_HINTS.get(token)
            if category and category in self._all_categories:
                hints.add(category)
        return hints

    def _expand_dependencies(self, categories: set[str]) -> set[str]:
        """Expand categories with their required_categories dependencies."""
        expanded = set(categories)
        for cat in categories:
            info = self._registry.plugin_for_category(cat)
            if info and info.required_categories:
                for dep in info.required_categories:
                    if dep in self._all_categories:
                        expanded.add(dep)
        return expanded

    def _build_prompt(self) -> str:
        """Build the router system prompt from registered category descriptions."""
        descriptions = self._registry.category_descriptions()
        lines = [
            f"- {cat}: {desc}" for cat, desc in sorted(descriptions.items())
        ]
        category_list = "\n".join(lines)
        return ROUTER_SYSTEM_PROMPT.format(category_list=category_list)
