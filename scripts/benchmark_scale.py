import os
import sys
import time
import json
import random
import statistics
from typing import List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.embeddings import embedding_engine
from backend.app.reranker import reranker

INDUSTRIES = [
    "Food Delivery & Quick Commerce",
    "Payments & Fintech",
    "Banking & Cards",
    "E-Commerce",
    "Automotive & Manufacturing",
    "Logistics & Supply Chain",
    "Travel & Hospitality",
    "Healthcare & Pharma"
]

SAMPLE_MANIFESTOS = {
    "Food Delivery & Quick Commerce": "Interested in grocery deals, restaurant offers, delivery logistics, packaging, and payment gateway partnerships.",
    "Payments & Fintech": "Interested in e-commerce promotions, food delivery festive discounts, card payment partnerships, UPI merchant cashback, and checkout offers.",
    "Banking & Cards": "Interested in credit card festive offers, dining discounts, merchant alliances, e-commerce checkout cashback, and consumer spend campaigns.",
    "E-Commerce": "Interested in festive sales, consumer electronics, fashion, logistics fulfillment, payment discounts, and co-marketing.",
    "Automotive & Manufacturing": "Interested in automotive spare parts, two-wheeler supply chain, EV battery technology, vehicle financing, and industrial machinery.",
    "Logistics & Supply Chain": "Interested in freight capacity, warehouse automation, last-mile delivery fleets, packaging supplies, and customs clearance.",
    "Travel & Hospitality": "Interested in airline alliances, hotel loyalty programs, corporate travel expense management, and luggage delivery.",
    "Healthcare & Pharma": "Interested in prescription delivery, diagnostic lab tie-ups, health insurance claims, and telemedicine checkout."
}

class SyntheticAgent:
    def __init__(self, idx: int):
        self.id = f"agent-uuid-{idx:05d}"
        self.company_name = f"EnterpriseCorp_{idx}"
        self.industry_category = random.choice(INDUSTRIES)
        self.interest_manifesto = SAMPLE_MANIFESTOS[self.industry_category]
        self.negative_interests = ""
        self.trust_score = random.uniform(0.8, 1.0)
        self.is_active = True
        self.total_notified = random.randint(0, 50)
        self.total_engaged = int(self.total_notified * random.uniform(0.1, 0.6))
        self.embedding = embedding_engine.embed_text(self.interest_manifesto)

def run_scale_benchmark(num_agents: int = 1000, num_posts: int = 20):
    print(f"\n=======================================================")
    print(f" AGENTPULSE SCALE BENCHMARK: {num_agents} AGENTS, {num_posts} POSTS")
    print(f"=======================================================")
    
    print(f"[*] Generating {num_agents} synthetic enterprise agents...")
    t0 = time.perf_counter()
    agents: List[SyntheticAgent] = [SyntheticAgent(i) for i in range(num_agents)]
    gen_time = time.perf_counter() - t0
    print(f"[+] {num_agents} agents generated with 256-d embeddings in {gen_time:.2f}s.\n")

    sample_post_title = "Diwali Food Delivery Discount"
    sample_post_content = "Swiggy offering flat 5% off on all delivery orders above ₹300 during Diwali week."
    author_company = "Swiggy"
    author_industry = "Food Delivery & Quick Commerce"

    stage1_latencies = []
    stage2_latencies = []
    stage3_latencies = []
    total_latencies = []
    notified_counts = []

    print("[*] Running multi-stage routing simulation across all agents...")

    for p_idx in range(num_posts):
        t_start = time.perf_counter()

        # Step 0: Embed post
        post_vec = embedding_engine.embed_text(f"{sample_post_title} {sample_post_content}")

        # Stage 1: Rule & Metadata Guardrail Filter
        t_s1 = time.perf_counter()
        stage1_candidates = [
            a for a in agents
            if a.company_name != author_company and a.is_active and a.trust_score >= 0.2
        ]
        s1_time = (time.perf_counter() - t_s1) * 1000
        stage1_latencies.append(s1_time)

        # Stage 2: Dense Vector ANN Match (Top K = 50)
        t_s2 = time.perf_counter()
        scored = [
            (a, embedding_engine.cosine_similarity(post_vec, a.embedding))
            for a in stage1_candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        top_k = scored[:50]
        s2_time = (time.perf_counter() - t_s2) * 1000
        stage2_latencies.append(s2_time)

        # Stage 3: Cross-Encoder & Synergy Reranker
        t_s3 = time.perf_counter()
        notified = []
        for a, v_score in top_k:
            score, rationale, is_notified = reranker.evaluate(
                post_title=sample_post_title,
                post_content=sample_post_content,
                author_company=author_company,
                author_industry=author_industry,
                target_agent=a,
                vector_score=v_score
            )
            if is_notified:
                notified.append(a)
        s3_time = (time.perf_counter() - t_s3) * 1000
        stage3_latencies.append(s3_time)

        tot_time = (time.perf_counter() - t_start) * 1000
        total_latencies.append(tot_time)
        notified_counts.append(len(notified))

    print("\n---------------- BENCHMARK RESULTS -------------------")
    print(f" Registered Agents (N)     : {num_agents}")
    print(f" Posts Ingested & Evaluated : {num_posts}")
    print(f" Avg Notified Agents/Post   : {statistics.mean(notified_counts):.1f}")
    print("------------------------------------------------------")
    print(f" Stage 1 (SQL Guardrails)   : Avg = {statistics.mean(stage1_latencies):.2f} ms | p95 = {statistics.quantiles(stage1_latencies, n=20)[-1]:.2f} ms")
    print(f" Stage 2 (Dense Vector ANN) : Avg = {statistics.mean(stage2_latencies):.2f} ms | p95 = {statistics.quantiles(stage2_latencies, n=20)[-1]:.2f} ms")
    print(f" Stage 3 (Reranker & Judge) : Avg = {statistics.mean(stage3_latencies):.2f} ms | p95 = {statistics.quantiles(stage3_latencies, n=20)[-1]:.2f} ms")
    print("------------------------------------------------------")
    print(f" Total End-to-End Latency   : Avg = {statistics.mean(total_latencies):.2f} ms | p95 = {statistics.quantiles(total_latencies, n=20)[-1]:.2f} ms")
    throughput = 1000.0 / statistics.mean(total_latencies)
    print(f" Peak Single-Worker Throughput: {throughput:.1f} posts/second")
    print("=======================================================\n")

if __name__ == "__main__":
    run_scale_benchmark(num_agents=1000, num_posts=20)
