"""
Benchmark Dataset Generator & Importer
Creates comprehensive student interaction datasets, item response matrices,
and industry career benchmarks for offline model training and calibration.
"""
import csv
import json
import os
import random
import math
from datetime import datetime, timedelta, timezone

DATASETS_DIR = os.path.dirname(os.path.abspath(__file__))

CONCEPTS = [
    {"concept": "Data Types & Mutability", "skill": "Python", "base_diff": -1.8},
    {"concept": "Control Flow & Generators", "skill": "Python", "base_diff": -0.7},
    {"concept": "Pandas DataFrames", "skill": "Python", "base_diff": -0.2},
    {"concept": "NumPy & Vectorization", "skill": "Python", "base_diff": 0.1},
    {"concept": "Python Concurrency & GIL", "skill": "Python", "base_diff": 0.8},
    {"concept": "SQL Querying & Joins", "skill": "SQL", "base_diff": -1.5},
    {"concept": "Window Functions", "skill": "SQL", "base_diff": 0.4},
    {"concept": "Database Indexing & Query Plans", "skill": "SQL", "base_diff": 1.2},
    {"concept": "Bias-Variance Tradeoff", "skill": "Machine Learning", "base_diff": -0.5},
    {"concept": "Evaluation Metrics", "skill": "Machine Learning", "base_diff": 0.3},
    {"concept": "Regularization & Loss Functions", "skill": "Machine Learning", "base_diff": 0.5},
    {"concept": "Gradient Boosting & Trees", "skill": "Machine Learning", "base_diff": 1.1},
    {"concept": "Hypothesis Testing & p-values", "skill": "Statistics", "base_diff": -0.4},
    {"concept": "Probability Distributions", "skill": "Statistics", "base_diff": 0.2},
    {"concept": "A/B Testing & Causal Inference", "skill": "Statistics", "base_diff": 1.0},
    {"concept": "Neural Network Fundamentals", "skill": "Deep Learning", "base_diff": 0.3},
    {"concept": "Transformers & Attention", "skill": "Deep Learning", "base_diff": 1.3},
    {"concept": "Caching & Consistency", "skill": "System Design", "base_diff": 0.4},
    {"concept": "Distributed Systems & Scalability", "skill": "System Design", "base_diff": 0.9},
    {"concept": "RESTful APIs & HTTP", "skill": "Backend Architecture", "base_diff": -0.3},
    {"concept": "Authentication & Security", "skill": "Backend Architecture", "base_diff": 0.2},
    {"concept": "Message Queues & Async Tasks", "skill": "Backend Architecture", "base_diff": 0.5},
    {"concept": "Time Complexity & Big-O", "skill": "Data Structures & Algorithms", "base_diff": -0.6},
    {"concept": "Graph Algorithms", "skill": "Data Structures & Algorithms", "base_diff": 0.6}
]

def generate_student_interaction_dataset(
    filename="student_interaction_logs.csv",
    num_students=500,
    interactions_per_student=25,
    is_adaptive=False
):
    """
    Generates realistic student interaction logs.
    If is_adaptive=True, questions target student weak concepts and simulate learning progression up to mastery.
    """
    filepath = os.path.join(DATASETS_DIR, filename)
    random.seed(42 if not is_adaptive else 100)
    
    rows = []
    base_time = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)

    for s_id in range(1, num_students + 1):
        student_id = f"STU_{s_id:04d}"
        initial_theta = random.gauss(0.1, 0.8)
        current_theta = initial_theta
        
        # Student concept masteries
        student_mastery = {c["concept"]: random.betavariate(2.0, 3.5) for c in CONCEPTS}
        student_time = base_time + timedelta(days=random.randint(0, 45), hours=random.randint(0, 12))

        for step in range(1, interactions_per_student + 1):
            if is_adaptive:
                # Target weaker concepts with 70% probability
                sorted_concepts = sorted(CONCEPTS, key=lambda c: student_mastery[c["concept"]])
                if random.random() < 0.70:
                    concept_data = random.choice(sorted_concepts[:8])
                else:
                    concept_data = random.choice(CONCEPTS)
            else:
                concept_data = random.choice(CONCEPTS)

            concept = concept_data["concept"]
            skill = concept_data["skill"]
            b_diff = concept_data["base_diff"] + random.uniform(-0.2, 0.2)
            a_disc = random.uniform(1.1, 1.8)
            
            # Probability of correct response under 2PL IRT + BKT mastery
            prob_irt = 1.0 / (1.0 + math.exp(-a_disc * (current_theta - b_diff)))
            curr_m = student_mastery[concept]
            p_correct = 0.45 * prob_irt + 0.55 * (curr_m * 0.92 + (1.0 - curr_m) * 0.18)
            
            is_correct = 1 if random.random() < p_correct else 0
            
            base_rt = 40 + max(0, b_diff * 12)
            response_time = max(10, int(random.gauss(base_rt, 10)))
            
            rows.append({
                "student_id": student_id,
                "step": step,
                "timestamp": student_time.isoformat(),
                "concept": concept,
                "skill": skill,
                "item_id": f"ITEM_{concept[:4].upper()}_{random.randint(1, 8):03d}",
                "irt_difficulty_b": round(b_diff, 3),
                "irt_discrimination_a": round(a_disc, 3),
                "student_theta": round(current_theta, 3),
                "prior_mastery": round(curr_m, 3),
                "is_correct": is_correct,
                "response_time_sec": response_time
            })
            
            # Learning transition
            learn_rate = 0.26 if is_adaptive else 0.18
            if is_correct:
                student_mastery[concept] = min(0.99, curr_m + (1.0 - curr_m) * learn_rate)
                current_theta = min(3.8, current_theta + 0.07)
            else:
                student_mastery[concept] = max(0.08, curr_m * 0.90)
                current_theta = max(-3.5, current_theta - 0.02)

            student_time += timedelta(minutes=random.randint(2, 5))

    fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[+] Successfully generated {len(rows)} student interaction logs in: {filepath}")
    return filepath

def generate_career_role_benchmarks(filename="career_role_benchmarks.json"):
    filepath = os.path.join(DATASETS_DIR, filename)
    benchmarks = {
        "roles": [
            {
                "role_id": "data_scientist",
                "title": "Data Scientist",
                "readiness_threshold": 78.0,
                "required_skills": {
                    "Python": {"weight": 0.25, "benchmark_mastery": 0.75, "min_theta": 0.50},
                    "Machine Learning": {"weight": 0.27, "benchmark_mastery": 0.80, "min_theta": 0.75},
                    "Statistics": {"weight": 0.20, "benchmark_mastery": 0.75, "min_theta": 0.60},
                    "SQL": {"weight": 0.18, "benchmark_mastery": 0.70, "min_theta": 0.40},
                    "Deep Learning": {"weight": 0.10, "benchmark_mastery": 0.65, "min_theta": 0.30}
                }
            },
            {
                "role_id": "backend_developer",
                "title": "Backend Developer",
                "readiness_threshold": 80.0,
                "required_skills": {
                    "Python": {"weight": 0.25, "benchmark_mastery": 0.80, "min_theta": 0.60},
                    "Backend Architecture": {"weight": 0.25, "benchmark_mastery": 0.85, "min_theta": 0.80},
                    "SQL": {"weight": 0.20, "benchmark_mastery": 0.75, "min_theta": 0.50},
                    "System Design": {"weight": 0.20, "benchmark_mastery": 0.75, "min_theta": 0.70},
                    "Data Structures & Algorithms": {"weight": 0.10, "benchmark_mastery": 0.70, "min_theta": 0.50}
                }
            },
            {
                "role_id": "data_analyst",
                "title": "Data Analyst",
                "readiness_threshold": 75.0,
                "required_skills": {
                    "SQL": {"weight": 0.35, "benchmark_mastery": 0.85, "min_theta": 0.65},
                    "Python": {"weight": 0.25, "benchmark_mastery": 0.70, "min_theta": 0.40},
                    "Statistics": {"weight": 0.25, "benchmark_mastery": 0.75, "min_theta": 0.50},
                    "Machine Learning": {"weight": 0.15, "benchmark_mastery": 0.60, "min_theta": 0.20}
                }
            }
        ],
        "metadata": {
            "version": "2026.1",
            "source": "Aggregated Industry Tech Hiring Rubrics",
            "total_roles": 3
        }
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(benchmarks, f, indent=2)

    print(f"[+] Successfully generated career benchmark rubric in: {filepath}")
    return filepath

if __name__ == "__main__":
    generate_student_interaction_dataset("student_interaction_logs.csv", num_students=500, interactions_per_student=25, is_adaptive=False)
    generate_student_interaction_dataset("adaptive_mastery_training_logs.csv", num_students=500, interactions_per_student=50, is_adaptive=True)
    generate_career_role_benchmarks("career_role_benchmarks.json")
