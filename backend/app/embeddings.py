import json
import re
import math
import numpy as np
from typing import List, Dict

# Domain semantic concept spaces mapped to specialized embedding dimensions
DOMAIN_TAXONOMY = {
    # Food Delivery & Quick Commerce
    "food_dining": ["food", "delivery", "dining", "restaurant", "meals", "swiggy", "zomato", "groceries", "kitchen", "dishes"],
    "quick_commerce": ["instant", "10-minute", "grocery", "dark store", "fmcg", "quick commerce", "blinkit", "zepto", "instamart"],
    
    # Fintech & Payments
    "upi_payments": ["upi", "qr code", "phonepe", "gpay", "paytm", "merchant", "checkout", "transaction", "digital wallet", "p2m"],
    "banking_cards": ["bank", "credit card", "debit card", "hdfc", "icici", "sbi", "reward points", "emi", "cashback", "pos"],
    "fintech_lending": ["loan", "credit line", "bnpl", "buy now pay later", "fintech", "underwriting", "interest rate", "nbfc"],
    
    # E-Commerce & Retail
    "e_commerce": ["ecommerce", "shopping", "flipkart", "amazon", "orders", "cart", "festive sale", "big billion", "great indian festival"],
    "promotions_discounts": ["discount", "flat off", "coupon", "cashback", "promo", "festive offer", "diwali", "savings", "deal", "voucher"],
    "logistics_fulfillment": ["warehouse", "shipping", "courier", "last mile", "fulfillment", "supply chain", "delhivery", "tracking"],
    
    # Automotive & Mobility
    "auto_manufacturing": ["automobile", "automotive", "bajaj", "tata motors", "vehicle", "engine", "chassis", "oem", "spare parts", "assembly"],
    "two_wheelers": ["bike", "motorcycle", "scooter", "two-wheeler", "pulsar", "activa", "riding", "commute", "dealership"],
    "electric_vehicles": ["ev", "electric vehicle", "battery", "charging station", "lithium", "clean mobility", "range", "inverter"],
    "fleet_commercial": ["commercial vehicle", "truck", "fleet leasing", "heavy machinery", "transport logistics", "haulage"],
    
    # Travel & Hospitality
    "travel_hospitality": ["flight", "hotel", "travel", "booking", "tourism", "vacation", "airline", "staycation"],
    
    # Healthcare & Pharma
    "health_pharma": ["pharmacy", "medicine", "doctor", "health", "hospital", "teleconsultation", "diagnostic", "prescription"]
}

TAXONOMY_KEYS = list(DOMAIN_TAXONOMY.keys())
NUM_TAXONOMY_DIMS = len(TAXONOMY_KEYS) * 4 # 14 * 4 = 56 dimensions
HASH_DIMS = 200 # Character n-gram and token hashing dimensions
TOTAL_EMBEDDING_DIM = NUM_TAXONOMY_DIMS + HASH_DIMS # 256 dimensions

class SemanticEmbeddingEngine:
    def __init__(self):
        self.dim = TOTAL_EMBEDDING_DIM

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'[^a-zA-Z0-9\s₹]', ' ', text.lower())

    def _extract_taxonomy_vector(self, text: str) -> np.ndarray:
        vec = np.zeros(NUM_TAXONOMY_DIMS, dtype=np.float32)
        words = set(re.findall(r'\b\w+\b', text))
        
        for i, (category, keywords) in enumerate(DOMAIN_TAXONOMY.items()):
            base_idx = i * 4
            matches = 0
            weighted_score = 0.0
            for kw in keywords:
                if " " in kw:
                    if kw in text:
                        matches += 2
                        weighted_score += 2.5
                else:
                    if kw in words:
                        matches += 1
                        weighted_score += 1.0
            
            if matches > 0:
                vec[base_idx] = float(matches)
                vec[base_idx + 1] = float(weighted_score)
                vec[base_idx + 2] = math.log1p(weighted_score)
                vec[base_idx + 3] = 1.0 # Category active indicator
                
        return vec

    def _extract_hash_vector(self, text: str) -> np.ndarray:
        vec = np.zeros(HASH_DIMS, dtype=np.float32)
        tokens = re.findall(r'\b\w+\b', text)
        for token in tokens:
            # Word level hashing
            h1 = hash(token) % HASH_DIMS
            vec[h1] += 1.0
            # Character 3-gram hashing for subword capture
            if len(token) >= 3:
                for j in range(len(token) - 2):
                    tri = token[j:j+3]
                    h2 = hash(tri) % HASH_DIMS
                    vec[h2] += 0.4
        return vec

    def embed_text(self, text: str) -> List[float]:
        cleaned = self._clean_text(text)
        tax_vec = self._extract_taxonomy_vector(cleaned)
        hash_vec = self._extract_hash_vector(cleaned)
        
        # Combine weighted taxonomy and hash vectors
        combined = np.concatenate([tax_vec * 2.5, hash_vec * 0.5])
        
        # L2 Normalization
        norm = np.linalg.norm(combined)
        if norm > 1e-9:
            combined = combined / norm
        else:
            combined = np.zeros(self.dim, dtype=np.float32)
            combined[0] = 1.0
            
        return [float(x) for x in combined.tolist()]

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2:
            return 0.0
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0
        dot = float(np.dot(a, b) / (norm_a * norm_b))
        # Clamp to [0.0, 1.0] for non-negative semantic similarity
        return max(0.0, min(1.0, dot))

    @staticmethod
    def update_vector(current_vec: List[float], target_vec: List[float], alpha: float) -> List[float]:
        """
        Dynamically shifts current_vec towards or away from target_vec:
        v_new = normalize(v_current + alpha * v_target)
        """
        a = np.array(current_vec, dtype=np.float32)
        b = np.array(target_vec, dtype=np.float32)
        updated = a + (alpha * b)
        norm = np.linalg.norm(updated)
        if norm > 1e-9:
            updated = updated / norm
        return [float(x) for x in updated.tolist()]

# Global singleton
embedding_engine = SemanticEmbeddingEngine()
