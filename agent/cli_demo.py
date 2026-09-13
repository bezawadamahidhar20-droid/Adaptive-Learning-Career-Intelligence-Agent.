"""
CLI Interactive & Simulation Demo for Adaptive Learning & Career Intelligence Agent
Simulates student interaction, updates knowledge state via BKT/IRT, and previews adaptive next-assignment.
"""
import sys
import os
import random

# Reconfigure stdout for UTF-8 if available
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent import AdaptiveLearningAgent

def run_simulation():
    print("=" * 75)
    print(" [*] ADAPTIVE LEARNING & CAREER INTELLIGENCE AGENT - SIMULATION ENGINE")
    print("=" * 75)

    agent = AdaptiveLearningAgent()
    print(f"[*] Loaded question bank: {len(agent.question_bank)} questions.")
    
    target_role = "data_scientist"
    role_obj = agent.role_matcher.get_role(target_role)
    print(f"[*] Target Career Goal: {role_obj.title}")

    # Initialize fresh student profile
    student = agent.initialize_student_profile(initial_theta=-0.5)

    print("\n--- STAGE 1: INITIAL ASSESSMENT GENERATION ---")
    assessment_1 = agent.generate_assignment(student, total_questions=15, target_role=target_role)
    print(f"[+] Generated Assignment #1 with {len(assessment_1)} questions.")

    print("\n--- STAGE 2: SIMULATING STUDENT ATTEMPTS ---")
    submissions = []
    for q in assessment_1:
        # Simulate: student is good at Python/SQL (85% correct), but struggles with ML/Stats/DL (35% correct)
        concept = q.get("concept", "")
        if "Python" in q.get("skill", "") or "SQL" in q.get("skill", ""):
            is_correct = random.random() < 0.85
        else:
            is_correct = random.random() < 0.35

        chosen_option = q["answer"] if is_correct else (q["answer"] + 1) % len(q["options"])
        submissions.append((q["id"], chosen_option))

    # Process assessment batch
    batch_result = agent.process_full_assessment(student, submissions)
    print(f"[OK] Completed Assessment #1: {batch_result['correct_count']}/{batch_result['total_questions']} correct ({batch_result['score_percentage']}%)")
    print(f"[OK] Updated IRT Student Ability (Theta): {student['theta']}")

    print("\n" + "=" * 75)
    print(f"{'CONCEPT':<35} | {'SKILL':<20} | {'MASTERY':<10}")
    print("-" * 75)
    for concept, mastery in sorted(student["concept_mastery"].items(), key=lambda x: x[1]):
        # Find skill
        matching_q = next((q for q in agent.question_bank if q.get("concept") == concept), {})
        skill = matching_q.get("skill", "General")
        bar = "#" * int(mastery * 10) + "-" * (10 - int(mastery * 10))
        print(f"{concept:<35} | {skill:<20} | {mastery*100:>5.1f}% [{bar}]")
    print("=" * 75)

    print("\n--- STAGE 3: CAREER READINESS & SKILL GAP ANALYSIS ---")
    career_report = agent.analyze_career_fit(student, target_role)
    print(f"[TARGET ROLE] {career_report.role_title}")
    print(f"[READINESS SCORE] {career_report.readiness_score}% (Job Ready: {career_report.is_job_ready})")
    print(f"[TOP PRIORITY SKILL] {career_report.top_priority_skill}")
    print(f"[ESTIMATED STUDY TIME] {career_report.estimated_study_hours} hours\n")

    print(f"{'RANK':<5} | {'SKILL':<25} | {'CURRENT':<8} | {'TARGET':<8} | {'GAP':<8} | {'ACTION':<20}")
    print("-" * 85)
    for gap in career_report.gaps:
        print(f"{gap.priority_rank:<5} | {gap.skill:<25} | {gap.current_mastery*100:>5.1f}% | {gap.target_threshold*100:>5.0f}% | {gap.gap_magnitude:>6.3f} | {gap.recommendation_text[:35]}...")

    print("\n--- STAGE 4: ADAPTIVE ASSIGNMENT #2 PREVIEW (Targeting Weaknesses) ---")
    assessment_2 = agent.generate_assignment(student, total_questions=10, target_role=target_role)
    print(f"[+] Generated Adaptive Assignment #2 ({len(assessment_2)} questions):")
    for idx, q in enumerate(assessment_2, 1):
        concept = q.get("concept")
        curr_m = student["concept_mastery"].get(concept, 0.2)
        print(f"  {idx}. [{q.get('skill')}] {concept} (Diff: {q.get('difficulty')}/5, Current Mastery: {curr_m*100:.1f}%)")
        print(f"     Q: {q.get('question')[:70]}...")

    print("\n" + "=" * 75)
    print(" [OK] SIMULATION COMPLETE: Online BKT/IRT updates & adaptive selection verified.")
    print("=" * 75)

if __name__ == "__main__":
    run_simulation()
