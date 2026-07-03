"""Spatio-Temporal Context Retriever — search web for place-time context.

In the MVP, this module generates search queries and saves them.
The actual retrieval is done by the agent (Cola) running the pipeline.
"""

import json
from pathlib import Path
from typing import Optional


class RetrievedContext:
    def __init__(self, place: str, story_period: str,
                 search_queries: list[str],
                 nearby_entities: Optional[list[dict]] = None,
                 period_context: Optional[list[dict]] = None,
                 uncertainties: Optional[list[str]] = None):
        self.place = place
        self.story_period = story_period
        self.search_queries = search_queries
        self.nearby_entities = nearby_entities or []
        self.period_context = period_context or []
        self.uncertainties = uncertainties or []

    def to_dict(self) -> dict:
        return {
            "place": self.place,
            "story_period": self.story_period,
            "search_queries": self.search_queries,
            "nearby_entities": self.nearby_entities,
            "period_context": self.period_context,
            "uncertainties": self.uncertainties,
        }

    def save(self, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


def build_search_queries(location: str, story_period: str) -> list[str]:
    """Generate search queries for place-time context retrieval."""
    return [
        f"{location} history {story_period}",
        f"{location} landmarks historical sites",
        f"{location} geography urban development",
        f"{location} culture community history",
        f"{location} what was there {story_period}",
    ]


def create_context(location: str, story_period: str) -> RetrievedContext:
    """Create a retrieval context with search queries."""
    queries = build_search_queries(location, story_period)
    return RetrievedContext(
        place=location,
        story_period=story_period,
        search_queries=queries,
    )


def merge_retrieved(context: RetrievedContext,
                    entities: list[dict],
                    period_info: list[dict],
                    uncertainties: list[str]) -> RetrievedContext:
    """Merge agent-retrieved data back into the context."""
    context.nearby_entities = entities
    context.period_context = period_info
    context.uncertainties = uncertainties
    return context
