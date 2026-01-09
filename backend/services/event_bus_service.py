"""
Event Bus Service - EventBridge-inspired routing for async handlers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

EventHandler = Callable[[Dict[str, Any]], Awaitable[Any]]


@dataclass
class EventRule:
    """Simple rule matcher for event routing."""
    name: str
    handler: EventHandler
    sources: Optional[List[str]] = None
    detail_types: Optional[List[str]] = None
    detail_pattern: Dict[str, List[str]] = field(default_factory=dict)

    def matches(self, event: Dict[str, Any]) -> bool:
        source = event.get("source")
        detail_type = event.get("detail_type")
        detail = event.get("detail", {})

        if self.sources and source not in self.sources:
            return False
        if self.detail_types and detail_type not in self.detail_types:
            return False

        for key, allowed_values in self.detail_pattern.items():
            value = detail.get(key)
            if allowed_values and value not in allowed_values:
                return False

        return True


class EventBusService:
    """Event bus inspired by AWS EventBridge."""

    def __init__(self) -> None:
        self._rules: List[EventRule] = []

    def register_rule(
        self,
        *,
        name: str,
        handler: EventHandler,
        sources: Optional[List[str]] = None,
        detail_types: Optional[List[str]] = None,
        detail_pattern: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        rule = EventRule(
            name=name,
            handler=handler,
            sources=sources,
            detail_types=detail_types,
            detail_pattern=detail_pattern or {},
        )
        self._rules.append(rule)

    async def publish(self, event: Dict[str, Any]) -> List[Any]:
        matches = [rule for rule in self._rules if rule.matches(event)]
        if not matches:
            logger.debug("No event bus rules matched event: %s", event)
            return []

        tasks = [rule.handler(event) for rule in matches]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for rule, result in zip(matches, results):
            if isinstance(result, Exception):
                logger.warning("Event rule %s failed: %s", rule.name, result)

        return results
