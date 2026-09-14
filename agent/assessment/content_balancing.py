"""
Content Balancing & Domain Quota Controller
Ensures balanced coverage across all target concepts and prevents single-concept overrepresentation.
"""

from typing import Dict, Any, List, Set, Optional


class ContentBalancer:
    def __init__(self, max_items_per_concept: int = 3):
        self.max_items_per_concept = max_items_per_concept

    def filter_by_quota(
        self,
        candidate_items: List[Dict[str, Any]],
        administered_concept_counts: Dict[str, int],
        untested_concepts: Set[str]
    ) -> List[Dict[str, Any]]:
        """
        Filters and prioritizes candidate items based on domain content quotas.
        If untested concepts exist, prioritizes them.
        """
        # If untested concepts exist, filter to items from untested concepts if available
        if untested_concepts:
            untested_candidates = [
                it for it in candidate_items
                if it.get("concept") in untested_concepts or it.get("concept_id") in untested_concepts
            ]
            if untested_candidates:
                return untested_candidates

        # Otherwise filter out items from concepts that exceeded max quota
        valid_candidates = [
            it for it in candidate_items
            if administered_concept_counts.get(it.get("concept", it.get("concept_id", "")), 0) < self.max_items_per_concept
        ]

        return valid_candidates if valid_candidates else candidate_items
