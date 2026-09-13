"""
Offline Evaluation & Policy Simulation Harness
Quantitatively evaluates and benchmarks:
1. Random Selection Policy (Baseline)
2. Fixed-Difficulty Selection Policy (Static Medium)
3. Adaptive Multi-Objective Policy (BKT + IRT Fisher Information + Bandits)

Evaluates simulated students over standardized assessment trajectories and computes:
- Mean Learning Gain per Question
- Final Concept Mastery Distribution
- Weak-Concept Remediation Coverage
- Psychometric Question Information Efficiency
- Accuracy distribution across item difficulty tiers
"""
import copy
import json
import math
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple

from agent.agent import AdaptiveLearningAgent
from agent.knowledge.bkt import BKTKnowledgeTracer
from agent.knowledge.irt import IRTModel
from agent.assessment.question_selector import AdaptiveQuestionSelector

@dataclass
class SimulationResult:
    policy_name: str
    total_students: int
    questions_per_session: int
    initial_mastery_mean: float
    final_mastery_mean: float
    mean_learning_gain_per_question: float
    weak_concept_coverage_pct: float
    average_fisher_information: float
    final_accuracy_pct: float
    accuracy_by_difficulty: Dict[str, float]
    concept_mastery_std: float

class StudentSimulator:
    """
    Reproducible synthetic learner with true latent ability (theta)
    and per-concept latent masteries.
    """
    def __init__(self, student_id: str, true_theta: float, true_masteries: Dict[str, float], learning_rate: float = 0.15):
        self.student_id = student_id
        self.true_theta = true_theta
        self.true_masteries = true_masteries.copy()
        self.learning_rate = learning_rate

    def simulate_response(self, question: Dict[str, Any], rng: random.Random) -> bool:
        """Simulates response probability using 2PL IRT + true concept mastery."""
        concept = question.get("concept", "General")
        a = question.get("irt_a", 1.0)
        b = question.get("irt_b", 0.0)
        
        # 2PL IRT probability
        p_irt = IRTModel.probability_correct(self.true_theta, a, b)
        m = self.true_masteries.get(concept, 0.20)
        
        # Blended probability of correct answer
        p_correct = 0.5 * p_irt + 0.5 * m
        p_correct = max(0.05, min(0.95, p_correct))
        
        is_correct = (rng.random() < p_correct)
        
        # Targeted concept learning effect upon answering
        gain = self.learning_rate * (1.0 - m) if is_correct else 0.6 * self.learning_rate * (1.0 - m)
        self.true_masteries[concept] = min(1.0, m + gain)
        
        return is_correct

def run_policy_simulation(
    policy_name: str,
    num_students: int = 100,
    questions_per_student: int = 20,
    seed: int = 42
) -> SimulationResult:
    """
    Executes a controlled, reproducible comparative simulation.
    """
    rng = random.Random(seed)
    agent = AdaptiveLearningAgent()
    bank = agent.question_bank
    concepts = list(set(q.get("concept", "") for q in bank if q.get("concept")))

    initial_masteries_all = []
    final_masteries_all = []
    weak_remediated_counts = []
    total_weak_counts = []
    fisher_infos_all = []
    all_answers_by_diff = {"easy": [], "medium": [], "hard": []}
    all_answers_total = []

    for i in range(num_students):
        student_rng = random.Random(seed + i * 1000 + 7)
        # Sample latent student ability
        true_theta = student_rng.gauss(0.0, 1.0)
        
        # Sample initial masteries with some weak concepts (< 0.40)
        true_masteries = {}
        for c in concepts:
            true_masteries[c] = max(0.05, min(0.95, student_rng.betavariate(1.5, 3.0)))
        
        student = StudentSimulator(f"sim_{i}", true_theta, true_masteries, learning_rate=0.25)
        
        # Estimated student profile inside agent
        student_profile = agent.initialize_student_profile(initial_theta=0.0)
        
        # Track initial estimated mastery
        init_m_mean = sum(student.true_masteries.values()) / len(concepts)
        initial_masteries_all.append(init_m_mean)
        
        initial_weak_concepts = {c for c, m in student.true_masteries.items() if m < 0.45}
        total_weak_counts.append(len(initial_weak_concepts))

        seen_q_ids = set()

        for step in range(questions_per_student):
            # Select question based on policy
            if policy_name == "random":
                available = [q for q in bank if q["id"] not in seen_q_ids]
                if not available:
                    available = bank
                chosen_q = student_rng.choice(available)
            elif policy_name == "fixed_difficulty":
                # Always pick difficulty 3 (medium)
                med_pool = [q for q in bank if q.get("difficulty") == 3 and q["id"] not in seen_q_ids]
                if not med_pool:
                    med_pool = [q for q in bank if q["id"] not in seen_q_ids] or bank
                chosen_q = student_rng.choice(med_pool)
            elif policy_name == "adaptive":
                chosen_q = agent.selector.select_best_question(
                    candidate_questions=bank,
                    student_theta=student_profile.get("theta", 0.0),
                    concept_mastery=student_profile.get("concept_mastery", {}),
                    attempt_history=student_profile.get("attempt_history", []),
                    excluded_ids=seen_q_ids
                )
                if not chosen_q:
                    chosen_q = student_rng.choice(bank)
            else:
                raise ValueError(f"Unknown policy: {policy_name}")

            seen_q_ids.add(chosen_q["id"])

            # Compute psychometric Fisher Information
            a = chosen_q.get("irt_a", 1.0)
            b = chosen_q.get("irt_b", 0.0)
            f_info = IRTModel.fisher_information(student_profile.get("theta", 0.0), a, b)
            fisher_infos_all.append(f_info)

            # Student answers question
            is_correct = student.simulate_response(chosen_q, student_rng)
            selected_opt = chosen_q["answer"] if is_correct else (chosen_q["answer"] + 1) % len(chosen_q.get("options", [1, 2]))

            diff = chosen_q.get("difficulty", 3)
            diff_key = "easy" if diff <= 2 else ("medium" if diff == 3 else "hard")
            all_answers_by_diff[diff_key].append(1 if is_correct else 0)
            all_answers_total.append(1 if is_correct else 0)

            # Agent updates knowledge states
            agent.process_answer(
                student_profile=student_profile,
                question_id=chosen_q["id"],
                selected_option=selected_opt
            )

        # Evaluate final true mastery
        final_m_mean = sum(student.true_masteries.values()) / len(concepts)
        final_masteries_all.append(final_m_mean)

        # Count weak concepts successfully remediated (raised above 0.55)
        remediated = sum(1 for c in initial_weak_concepts if student.true_masteries[c] >= 0.55)
        weak_remediated_counts.append(remediated)

    # Compute aggregate metrics
    init_mean = sum(initial_masteries_all) / len(initial_masteries_all)
    fin_mean = sum(final_masteries_all) / len(final_masteries_all)
    gain_per_q = (fin_mean - init_mean) / questions_per_student
    
    tot_weak = sum(total_weak_counts)
    cov_pct = (sum(weak_remediated_counts) / max(1, tot_weak)) * 100.0
    
    avg_fisher = sum(fisher_infos_all) / max(1, len(fisher_infos_all))
    acc_pct = (sum(all_answers_total) / max(1, len(all_answers_total))) * 100.0

    acc_by_diff = {
        k: round((sum(v) / max(1, len(v))) * 100.0, 2) for k, v in all_answers_by_diff.items()
    }

    # Concept mastery standard deviation
    variance = sum((x - fin_mean) ** 2 for x in final_masteries_all) / len(final_masteries_all)
    std_dev = math.sqrt(variance)

    return SimulationResult(
        policy_name=policy_name,
        total_students=num_students,
        questions_per_session=questions_per_student,
        initial_mastery_mean=round(init_mean * 100.0, 2),
        final_mastery_mean=round(fin_mean * 100.0, 2),
        mean_learning_gain_per_question=round(gain_per_q * 100.0, 3),
        weak_concept_coverage_pct=round(cov_pct, 2),
        average_fisher_information=round(avg_fisher, 4),
        final_accuracy_pct=round(acc_pct, 2),
        accuracy_by_difficulty=acc_by_diff,
        concept_mastery_std=round(std_dev * 100.0, 2)
    )

def run_benchmark_suite() -> Dict[str, SimulationResult]:
    """Runs comparative evaluation across all 3 question selection strategies."""
    policies = ["random", "fixed_difficulty", "adaptive"]
    results = {}
    print("=" * 80)
    print("RUNNING REPRODUCIBLE ADAPTIVE LEARNING SIMULATION BENCHMARK (N=100 Students)")
    print("=" * 80)
    
    for pol in policies:
        print(f"Simulating Policy: {pol}...")
        res = run_policy_simulation(pol, num_students=100, questions_per_student=20, seed=42)
        results[pol] = res

    print("\n" + "=" * 80)
    print(f"{'Metric':<38} | {'Random':<12} | {'Fixed-Diff':<12} | {'Adaptive (BKT+IRT)':<18}")
    print("-" * 80)
    print(f"{'Initial Mastery':<38} | {results['random'].initial_mastery_mean:>10.2f}% | {results['fixed_difficulty'].initial_mastery_mean:>10.2f}% | {results['adaptive'].initial_mastery_mean:>16.2f}%")
    print(f"{'Final Mastery':<38} | {results['random'].final_mastery_mean:>10.2f}% | {results['fixed_difficulty'].final_mastery_mean:>10.2f}% | {results['adaptive'].final_mastery_mean:>16.2f}%")
    print(f"{'Mean Gain / Question':<38} | {results['random'].mean_learning_gain_per_question:>10.3f}% | {results['fixed_difficulty'].mean_learning_gain_per_question:>10.3f}% | {results['adaptive'].mean_learning_gain_per_question:>16.3f}%")
    print(f"{'Weak-Concept Remediation Rate':<38} | {results['random'].weak_concept_coverage_pct:>10.2f}% | {results['fixed_difficulty'].weak_concept_coverage_pct:>10.2f}% | {results['adaptive'].weak_concept_coverage_pct:>16.2f}%")
    print(f"{'Mean Fisher Information (Efficiency)':<38} | {results['random'].average_fisher_information:>10.4f}  | {results['fixed_difficulty'].average_fisher_information:>10.4f}  | {results['adaptive'].average_fisher_information:>16.4f} ")
    print(f"{'Overall Response Accuracy':<38} | {results['random'].final_accuracy_pct:>10.2f}% | {results['fixed_difficulty'].final_accuracy_pct:>10.2f}% | {results['adaptive'].final_accuracy_pct:>16.2f}%")
    print("=" * 80)
    return results

if __name__ == "__main__":
    run_benchmark_suite()
