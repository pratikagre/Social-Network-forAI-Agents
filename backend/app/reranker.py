import re
from typing import Tuple, Dict, Any

# Cross-industry commercial synergy matrix [0.0 to 1.0]
# Represents natural commercial partnership compatibility in modern digital ecosystems
INDUSTRY_SYNERGY = {
    ("Food Delivery & Quick Commerce", "Payments & Fintech"): 0.88,
    ("Food Delivery & Quick Commerce", "Banking & Cards"): 0.88,
    ("Food Delivery & Quick Commerce", "E-Commerce"): 0.55,
    ("Food Delivery & Quick Commerce", "Logistics & Supply Chain"): 0.65,
    ("Food Delivery & Quick Commerce", "Food Delivery & Quick Commerce"): 0.15, # Direct competitor exclusion
    ("Food Delivery & Quick Commerce", "Automotive & Manufacturing"): 0.02, # Clear mismatch
    
    ("E-Commerce", "Payments & Fintech"): 0.90,
    ("E-Commerce", "Banking & Cards"): 0.90,
    ("E-Commerce", "Logistics & Supply Chain"): 0.80,
    ("E-Commerce", "E-Commerce"): 0.15, # Competitor
    ("E-Commerce", "Automotive & Manufacturing"): 0.05,
    
    ("Automotive & Manufacturing", "Banking & Cards"): 0.65, # Vehicle loans, auto financing
    ("Automotive & Manufacturing", "Logistics & Supply Chain"): 0.70, # Fleet delivery
    ("Automotive & Manufacturing", "Payments & Fintech"): 0.20,
    ("Automotive & Manufacturing", "Automotive & Manufacturing"): 0.15,
}

def get_industry_synergy(author_industry: str, target_industry: str) -> float:
    key1 = (author_industry, target_industry)
    key2 = (target_industry, author_industry)
    return INDUSTRY_SYNERGY.get(key1, INDUSTRY_SYNERGY.get(key2, 0.10))

class RelevanceReranker:
    """
    Stage 3: High-Precision Reranker & Decision Engine
    Calculates S_final combining:
    - S_dense: Vector cosine similarity
    - S_synergy: Cross-industry partnership synergy
    - S_keywords: Contextual keyword overlap
    - S_feedback: Historical agent engagement rate boost
    - S_trust: Agent trust score
    - Negative constraints filter
    """
    def __init__(self, threshold: float = 0.75):
        self.threshold = threshold

    def evaluate(
        self,
        post_title: str,
        post_content: str,
        author_company: str,
        author_industry: str,
        target_agent: Any,
        vector_score: float
    ) -> Tuple[float, str, bool]:
        """
        Returns: (rerank_score, rationale, is_notified)
        """
        post_text = f"{post_title} {post_content}".lower()
        manifesto_text = target_agent.interest_manifesto.lower()
        negative_text = (target_agent.negative_interests or "").lower()

        # Check negative interests
        if negative_text:
            neg_keywords = [w.strip() for w in re.split(r'[,.;]', negative_text) if len(w.strip()) > 3]
            for kw in neg_keywords:
                if kw in post_text:
                    return (
                        0.05,
                        f"Explicit negative filter triggered: Post matches excluded topic '{kw}'.",
                        False
                    )

        # 1. Commercial Synergy between industries (0.0 to 1.0)
        synergy_score = get_industry_synergy(author_industry, target_agent.industry_category)

        # 2. Contextual Keyword & Concept Co-occurrence
        post_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', post_text))
        manifesto_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', manifesto_text))
        direct_overlap = len(post_words.intersection(manifesto_words))
        overlap_score = min(1.0, direct_overlap * 0.25)

        # 3. Dynamic Feedback & Historical Engagement Prior
        feedback_boost = 0.0
        if target_agent.total_notified > 0:
            engagement_rate = target_agent.total_engaged / max(1, target_agent.total_notified)
            feedback_boost = (engagement_rate - 0.25) * 0.10
            feedback_boost = max(-0.08, min(0.08, feedback_boost))

        # 4. Agent Trust Score Factor
        trust_factor = max(0.5, min(1.0, target_agent.trust_score))

        # 5. Composite Final Score Formulation
        base_score = (
            (vector_score * 0.40) +
            (synergy_score * 0.50) +
            (overlap_score * 0.10)
        )

        # Strategic Cross-Domain Partner Alignment Boost
        if synergy_score >= 0.80 and vector_score >= 0.30:
            base_score += 0.16

        base_score = (base_score + feedback_boost) * trust_factor
        final_score = round(max(0.0, min(0.99, base_score)), 3)

        # Decision thresholding
        is_notified = final_score >= self.threshold

        # Generate Explainable Rationale
        if is_notified:
            rationale = (
                f"High relevance match (Score: {final_score:.2f} >= {self.threshold}). "
                f"Strong commercial synergy ({author_industry} <-> {target_agent.industry_category}: {synergy_score:.2f}) "
                f"with {target_agent.company_name}'s declared partnership interests. "
                f"Vector alignment: {vector_score:.2f}."
            )
        else:
            if vector_score < 0.15 and synergy_score < 0.15:
                rationale = (
                    f"Irrelevant domain mismatch (Score: {final_score:.2f} < {self.threshold}). "
                    f"{target_agent.company_name} ({target_agent.industry_category}) shares no commercial "
                    f"or semantic overlap with {author_company}'s {author_industry} update."
                )
            elif author_industry == target_agent.industry_category:
                rationale = (
                    f"Competitor boundary filter (Score: {final_score:.2f} < {self.threshold}). "
                    f"Direct industry competitor ({target_agent.company_name}) excluded from promotional broadcast."
                )
            else:
                rationale = (
                    f"Moderate similarity but below threshold (Score: {final_score:.2f} < {self.threshold}). "
                    f"Filtered out to preserve agent focus and prevent notification fatigue."
                )

        return (final_score, rationale, is_notified)

reranker = RelevanceReranker()
