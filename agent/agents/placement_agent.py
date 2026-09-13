"""
Placement Preparation Agent
Generates comprehensive role-specific placement preparation modules:
1. Technical Coding & DSA Challenges
2. Quantitative & Logical Aptitude Practice
3. Technical & Behavioral / HR Interview Question Bank with Model Answers
4. Career Profile & Resume Checklists
"""
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class PlacementModule:
    module_type: str
    title: str
    description: str
    items: List[Dict[str, Any]]

class PlacementAgent:
    def get_placement_modules(self, target_role: str) -> List[PlacementModule]:
        """Returns personalized placement preparation curriculum for the target role."""
        
        # 1. Technical DSA Modules
        dsa_items = [
            {
                "id": "DSA_01",
                "title": "Two Sum / Two Pointers Technique",
                "difficulty": "Easy",
                "topic": "Arrays & Hash Tables",
                "problem": "Given an array of integers and a target sum, return indices of two numbers that add up to target in O(N) time.",
                "key_concept": "Hash Table O(1) complement lookup.",
                "solution_approach": "Use a dictionary to store seen values and their index. For each element num, check if (target - num) is in dict."
            },
            {
                "id": "DSA_02",
                "title": "Merge Intervals / Interval Overlap",
                "difficulty": "Medium",
                "topic": "Sorting & Intervals",
                "problem": "Given a collection of intervals, merge all overlapping intervals into non-overlapping spans.",
                "key_concept": "Sort by start time; iterate and merge if curr.start <= prev.end.",
                "solution_approach": "Sort intervals by start ascending. Iterate through; if current interval overlaps with previous, extend previous.end = max(prev.end, curr.end)."
            },
            {
                "id": "DSA_03",
                "title": "LRU Cache Implementation",
                "difficulty": "Medium",
                "topic": "Hash Table + Doubly Linked List",
                "problem": "Design a data structure that follows the constraints of a Least Recently Used (LRU) cache with O(1) get and put.",
                "key_concept": "Hash Map pointing to Doubly Linked List Nodes.",
                "solution_approach": "Combine HashMap for O(1) key-to-node lookup and a Doubly Linked List with dummy head and tail for O(1) node removal and insertion at head."
            },
            {
                "id": "DSA_04",
                "title": "Breadth-First Search & Shortest Path",
                "difficulty": "Medium",
                "topic": "Graphs & Queues",
                "problem": "Find the shortest path from start node to target in an unweighted graph.",
                "key_concept": "Queue-based level-order traversal with a visited set.",
                "solution_approach": "Use collections.deque; pop front, inspect unvisited neighbors, mark visited and record distance."
            }
        ]

        # 2. Aptitude Modules
        aptitude_items = [
            {
                "id": "APT_01",
                "title": "Probability & Combinatorics in Tech Interviews",
                "question": "A bag contains 4 red and 6 blue balls. Two balls are drawn at random without replacement. What is the probability that both are red?",
                "options": ["2/15", "4/15", "1/5", "3/10"],
                "correct_option": 0,
                "explanation": "P(1st Red) = 4/10. P(2nd Red | 1st Red) = 3/9. P(Both) = (4/10) * (3/9) = 12/90 = 2/15."
            },
            {
                "id": "APT_02",
                "title": "Time & Work Efficiency",
                "question": "Worker A can complete a data pipeline in 6 hours, while Worker B can complete it in 12 hours. How long will it take working together?",
                "options": ["4 hours", "3.5 hours", "5 hours", "4.5 hours"],
                "correct_option": 0,
                "explanation": "Combined rate = 1/6 + 1/12 = 3/12 = 1/4 pipeline/hour. Time = 4 hours."
            },
            {
                "id": "APT_03",
                "title": "Logical Deduction & Data Interpretation",
                "question": "If all Neural Networks are Function Approximators, and some Function Approximators are Linear, which conclusion definitely follows?",
                "options": [
                    "All Neural Networks are Linear",
                    "Some Neural Networks might be Linear",
                    "No Neural Network is Linear",
                    "All Function Approximators are Neural Networks"
                ],
                "correct_option": 1,
                "explanation": "Neural networks are a subset of function approximators; since some function approximators are linear, neural networks could intersect with linear models (e.g., single-layer perceptron without activation)."
            }
        ]

        # 3. Technical & HR Interview Question Bank
        interview_items = [
            {
                "id": "INT_01",
                "type": "technical",
                "question": "Explain the difference between Bias and Variance, and how regularization addresses them.",
                "model_answer": "Bias is error from erroneous assumptions in the learning algorithm (underfitting, high training error). Variance is error from sensitivity to small fluctuations in the training set (overfitting, high test error). Regularization (L1/L2) adds a penalty on large weights to loss function, constraining model complexity and reducing variance at the expense of slight bias increase."
            },
            {
                "id": "INT_02",
                "type": "technical",
                "question": "How does an SQL query execution engine optimize a query with multiple JOINs and WHERE clauses?",
                "model_answer": "The query optimizer uses cost-based models (CBO) and table statistics to determine: (1) predicate pushdown (filtering rows before joins), (2) index selection (B-Tree/Bitmap), (3) join order (driving table with smallest cardinality first), and (4) join algorithm (Hash Join, Merge Join, or Nested Loop)."
            },
            {
                "id": "INT_03",
                "type": "behavioral_hr",
                "question": "Tell me about a time you diagnosed and resolved a difficult technical bug under a tight deadline (STAR Method).",
                "model_answer": "Situation: In our college project, the API response times degraded to >5s under concurrent testing 2 days before demo. Task: I was responsible for diagnosing the bottleneck. Action: I profiled the FastAPI service, identified an N+1 query loop in our ORM database fetching, and refactored it into an eager-loaded batch SQL query with Redis caching. Result: Latency dropped from 5.2s to 48ms, and the project demo scored top marks."
            },
            {
                "id": "INT_04",
                "type": "behavioral_hr",
                "question": "Why are you interested in our company and this specific engineering track?",
                "model_answer": "Highlight specific interest in company's core engineering problems, showcase your continuous learning portfolio (adaptive mastery, projects), and articulate how your technical foundation in system design and data analytics creates immediate value."
            }
        ]

        # 4. Career Profile & Resume Checklists
        checklist_items = [
            {
                "id": "CHK_01",
                "title": "ATS-Optimized Resume Formatting",
                "description": "Ensure 1-page PDF format with clean standard fonts, quantifiable STAR bullet points, and exact target role keywords.",
                "is_essential": True
            },
            {
                "id": "CHK_02",
                "title": "GitHub Portfolio Showcase",
                "description": "Have at least 2 pinned repositories with clear READMEs, architecture diagrams, live demo links, and clean commit history.",
                "is_essential": True
            },
            {
                "id": "CHK_03",
                "title": "LinkedIn Professional Presence",
                "description": "Professional headshot, targeted headline matching role, detailed summary of technical projects, and active tech posts.",
                "is_essential": True
            }
        ]

        return [
            PlacementModule(
                module_type="dsa",
                title="Technical Coding & DSA Challenge Bank",
                description="Core algorithmic patterns frequently tested in technical hiring rounds.",
                items=dsa_items
            ),
            PlacementModule(
                module_type="aptitude",
                title="Quantitative & Logical Aptitude",
                description="Timed aptitude problems from major tech recruitment assessment patterns.",
                items=aptitude_items
            ),
            PlacementModule(
                module_type="interview_qa",
                title="Technical & HR Interview Question Bank",
                description="Curated technical deep-dives and STAR-method behavioral responses.",
                items=interview_items
            ),
            PlacementModule(
                module_type="resume_checklist",
                title="Resume, GitHub & Portfolio Readiness",
                description="Essential industry checklist to pass initial recruiter screenings.",
                items=checklist_items
            )
        ]
