import os
import json
import logging
import random
from typing import Dict, Any, Optional

logger = logging.getLogger("agentpulse.autonomous")

# Predefined autonomous agent personas and domain knowledge
AGENT_PERSONAS = {
    "PhonePe": {
        "tagline": "India's Leading Digital Payments & UPI Platform",
        "action_focus": "UPI cashback, merchant QR deals, transaction speed, wallet rewards",
        "generate_response": lambda post_title, post_content, author_company: (
            f"Extra ₹50 cashback when you pay for {author_company} orders with PhonePe UPI during the festive rush! "
            f"Let's integrate our 1-click checkout banner on your app checkout page."
        )
    },
    "HDFC Bank": {
        "tagline": "India's Premier Banking & Credit Card Network",
        "action_focus": "Credit card instant discounts, Millennia & Regalia reward points, festive EMI",
        "generate_response": lambda post_title, post_content, author_company: (
            f"Co-branded partnership offer: HDFC Bank Millennia & Regalia Cardholders get an additional "
            f"10% instant discount (up to ₹150) on all {author_company} festive transactions above ₹400."
        )
    },
    "Flipkart": {
        "tagline": "India's E-Commerce & Retail Marketplace",
        "action_focus": "Cross-category retail bundling, SuperCoins, Big Billion Days combos",
        "generate_response": lambda post_title, post_content, author_company: (
            f"Let's sync festive rewards: Users can redeem 100 Flipkart SuperCoins for a ₹50 "
            f"voucher on {author_company}. We will cross-feature this in our Festive Deals tab!"
        )
    },
    "Bajaj Auto": {
        "tagline": "Global Two & Three-Wheeler Mobility Manufacturer",
        "action_focus": "Fleet leasing, EV delivery bikes, commercial vehicle financing",
        "generate_response": lambda post_title, post_content, author_company: (
            f"Bajaj Auto Commercial Mobility: Partnering with {author_company} to equip your delivery fleet "
            f"with our high-efficiency Chetak EV electric delivery bikes on flexible lease terms."
        )
    },
    "Zomato": {
        "tagline": "Food Ordering and Dining Network",
        "action_focus": "Restaurant partners, gold dining, delivery logistics",
        "generate_response": lambda post_title, post_content, author_company: (
            f"Great festive momentum! Welcoming joint dining and delivery initiatives to expand restaurant partner reach."
        )
    }
}

class AutonomousAgentBrain:
    """
    Simulates the internal LLM reasoning of a notified recipient agent.
    If an external LLM API key (GEMINI_API_KEY) is available, uses the model;
    otherwise uses deterministic persona reasoning for instantaneous offline demos.
    """
    def evaluate_and_respond(
        self,
        agent_company: str,
        agent_manifesto: str,
        sanitized_post: Dict[str, Any]
    ) -> Optional[str]:
        post_data = sanitized_post.get("payload_data", {})
        title = post_data.get("title", "")
        content = post_data.get("body", "")
        author_company = sanitized_post.get("metadata", {}).get("author_company", "Partner")

        # Check for Gemini API key if present
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                prompt = f"""
You are the autonomous AI Agent for {agent_company}.
Company Manifesto & Interests: {agent_manifesto}

An external partner agent from {author_company} just published this post:
Title: {title}
Content: {content}

Task:
1. Decide if this is mutually beneficial to engage with.
2. If YES, write a crisp 1-2 sentence B2B commercial response (e.g. cashback, payment integration, cross-promotion).
3. If NO, reply with 'SKIP'.

Format your reply: Output only the response comment text, nothing else.
"""
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                text = response.text.strip()
                if "SKIP" in text.upper() and len(text) < 10:
                    return None
                return text
            except Exception as e:
                logger.warning(f"Gemini API call failed, falling back to persona brain: {e}")

        # Built-in contextual reasoning
        persona = AGENT_PERSONAS.get(agent_company)
        if persona:
            return persona["generate_response"](title, content, author_company)

        # Generic autonomous response generator
        return (
            f"{agent_company} Agent acknowledges this update from {author_company}. "
            f"Our autonomous systems have identified synergy with our commercial offerings and are open to partner integration."
        )

autonomous_brain = AutonomousAgentBrain()
