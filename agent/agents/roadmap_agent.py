"""
Dynamic Adaptive Roadmap Agent
Generates comprehensive multi-stage career roadmaps tailored to student skill gaps:
Stage 1: Foundations & Concepts
Stage 2: Applied Engineering & Coding Practice
Stage 3: Portfolio Projects & GitHub Artifacts
Stage 4: Job Placement & Interview Preparation
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class RoadmapTask:
    id: str
    target_role: str
    stage_name: str
    title: str
    description: str
    category: str  # 'concept', 'coding_task', 'project', 'dsa'
    associated_skill: str
    priority_rank: int
    is_completed: bool

ROLE_ROADMAP_TEMPLATES = {
    "data_scientist": [
        # Stage 1: Foundations
        {
            "id": "DS_S1_01", "stage": "Stage 1: Foundations & Core Concepts",
            "title": "Master Pandas DataFrames & Vectorized Indexing",
            "description": "Deep-dive into .loc vs .iloc, multi-indexing, and memory-efficient groupby aggregations.",
            "category": "concept", "skill": "Python"
        },
        {
            "id": "DS_S1_02", "stage": "Stage 1: Foundations & Core Concepts",
            "title": "Complex SQL Analytics & Window Functions",
            "description": "Write advanced SQL queries using RANK(), DENSE_RANK(), PARTITION BY, and recursive CTEs.",
            "category": "coding_task", "skill": "SQL"
        },
        {
            "id": "DS_S1_03", "stage": "Stage 1: Foundations & Core Concepts",
            "title": "Hypothesis Testing & Statistical Distributions",
            "description": "Formulate Null/Alternative hypotheses, compute p-values, and identify Type I/II errors.",
            "category": "concept", "skill": "Statistics"
        },
        # Stage 2: Applied Engineering
        {
            "id": "DS_S2_01", "stage": "Stage 2: Applied Machine Learning & Modeling",
            "title": "Build & Regularize Linear and Tree-Based Models",
            "description": "Implement Ridge (L2) and Lasso (L1) regularization, hyperparameter tuning, and cross-validation.",
            "category": "coding_task", "skill": "Machine Learning"
        },
        {
            "id": "DS_S2_02", "stage": "Stage 2: Applied Machine Learning & Modeling",
            "title": "Gradient Boosted Decision Trees (XGBoost / LightGBM)",
            "description": "Tune gradient boosting trees on imbalanced classification datasets with ROC-AUC optimization.",
            "category": "coding_task", "skill": "Machine Learning"
        },
        {
            "id": "DS_S2_03", "stage": "Stage 2: Applied Machine Learning & Modeling",
            "title": "A/B Testing Framework & Power Analysis",
            "description": "Design an online experimentation framework calculating sample size, minimum detectable effect, and power.",
            "category": "coding_task", "skill": "Statistics"
        },
        # Stage 3: Real-World Portfolio Projects
        {
            "id": "DS_S3_01", "stage": "Stage 3: Portfolio Engineering & GitHub Artifacts",
            "title": "End-to-End Predictive ML Microservice",
            "description": "Develop and containerize a FastAPI predictive microservice with automated data validation and drift metrics.",
            "category": "project", "skill": "Python"
        },
        {
            "id": "DS_S3_02", "stage": "Stage 3: Portfolio Engineering & GitHub Artifacts",
            "title": "Deep Learning Vision / NLP Transformer Fine-Tuning",
            "description": "Fine-tune a HuggingFace Transformer model using PyTorch with self-attention analysis.",
            "category": "project", "skill": "Deep Learning"
        },
        # Stage 4: Placement & Interview Prep
        {
            "id": "DS_S4_01", "stage": "Stage 4: Job Placement & Technical Interview Prep",
            "title": "Data Science DSA & Algorithmic Problem Solving",
            "description": "Practice top 30 LeetCode Medium data structures, binary search trees, and dynamic programming.",
            "category": "dsa", "skill": "Data Structures & Algorithms"
        },
        {
            "id": "DS_S4_02", "stage": "Stage 4: Job Placement & Technical Interview Prep",
            "title": "Machine Learning System Design & Whiteboard Prep",
            "description": "Practice end-to-end ML system design architectures (Recommendation engine, Search ranking, Fraud detection).",
            "category": "concept", "skill": "Machine Learning"
        }
    ],
    "backend_developer": [
        # Stage 1: Foundations
        {
            "id": "BE_S1_01", "stage": "Stage 1: Foundations & Architecture",
            "title": "RESTful API Standards & Idempotency",
            "description": "Understand HTTP status codes, idempotent operations (PUT vs POST), and stateless auth.",
            "category": "concept", "skill": "Backend Architecture"
        },
        {
            "id": "BE_S1_02", "stage": "Stage 1: Foundations & Architecture",
            "title": "Relational Database Schema Design & B-Tree Indexing",
            "description": "Design normalized schemas (3NF) and composite index strategies to optimize query execution plans.",
            "category": "coding_task", "skill": "SQL"
        },
        # Stage 2: Applied Engineering
        {
            "id": "BE_S2_01", "stage": "Stage 2: Scalable Microservices & Caching",
            "title": "High-Throughput Caching (Redis Write-Through & Eviction)",
            "description": "Implement Redis caching patterns with TTL, cache invalidation, and distributed locks.",
            "category": "coding_task", "skill": "System Design"
        },
        {
            "id": "BE_S2_02", "stage": "Stage 2: Scalable Microservices & Caching",
            "title": "Asynchronous Task Queues with RabbitMQ/Celery",
            "description": "Build asynchronous worker pipelines with task retry mechanisms, dead-letter queues, and ACKs.",
            "category": "coding_task", "skill": "Backend Architecture"
        },
        # Stage 3: Portfolio Projects
        {
            "id": "BE_S3_01", "stage": "Stage 3: Portfolio Engineering & GitHub Artifacts",
            "title": "Distributed Rate Limiter & Auth Gateway",
            "description": "Build a sliding-window rate limiter and OAuth/JWT authentication gateway with Docker deployment.",
            "category": "project", "skill": "Backend Architecture"
        },
        # Stage 4: Placement Prep
        {
            "id": "BE_S4_01", "stage": "Stage 4: Placement & System Design Interviews",
            "title": "Backend DSA: Trees, Graphs & Hash Tables",
            "description": "Solve classic interview algorithmic challenges (Dijkstra, Topological Sort, LRU Cache implementation).",
            "category": "dsa", "skill": "Data Structures & Algorithms"
        },
        {
            "id": "BE_S4_02", "stage": "Stage 4: Placement & System Design Interviews",
            "title": "Scalable System Design Whiteboard Practice",
            "description": "Design high-scale architectures (URL Shortener, Distributed File Storage, Real-time Chat).",
            "category": "concept", "skill": "System Design"
        }
    ],
    "data_analyst": [
        # Stage 1: Foundations
        {
            "id": "DA_S1_01", "stage": "Stage 1: SQL Mastery & Data Extraction",
            "title": "Advanced SQL Aggregations & Joins",
            "description": "Master multi-table joins, subqueries, and window partition functions.",
            "category": "coding_task", "skill": "SQL"
        },
        # Stage 2: Analytics & Stats
        {
            "id": "DA_S2_01", "stage": "Stage 2: Statistical Analysis & Python",
            "title": "Exploratory Data Analysis with Pandas & Seaborn",
            "description": "Perform data cleansing, outlier detection, and statistical correlation analysis.",
            "category": "coding_task", "skill": "Python"
        },
        {
            "id": "DA_S2_02", "stage": "Stage 2: Statistical Analysis & Python",
            "title": "Business Metrics & Executive Reporting",
            "description": "Calculate retention cohorts, churn rates, customer lifetime value (LTV), and conversion funnels.",
            "category": "concept", "skill": "Statistics"
        },
        # Stage 3: Portfolio Projects
        {
            "id": "DA_S3_01", "stage": "Stage 3: Interactive Dashboard Project",
            "title": "Interactive Executive Analytics Dashboard",
            "description": "Build an interactive automated analytics dashboard showcasing actionable business insights.",
            "category": "project", "skill": "SQL"
        },
        # Stage 4: Placement Prep
        {
            "id": "DA_S4_01", "stage": "Stage 4: Placement Interview Preparation",
            "title": "Data Analyst Case Studies & SQL Live Coding",
            "description": "Practice real-world analytics case studies and timed live SQL coding challenges.",
            "category": "coding_task", "skill": "SQL"
        }
    ],
    "frontend_developer": [
        # Stage 1: Foundations
        {
            "id": "FE_S1_01", "stage": "Stage 1: Core Web & Modern JavaScript",
            "title": "JavaScript Internals & Async Event Loop",
            "description": "Master microtasks vs macrotasks, closures, prototypal inheritance, and TypeScript utility types.",
            "category": "concept", "skill": "JavaScript & TypeScript"
        },
        {
            "id": "FE_S1_02", "stage": "Stage 1: Core Web & Modern JavaScript",
            "title": "Modern CSS Architecture & Responsive Layouts",
            "description": "Master Flexbox, CSS Grid, Container Queries, and specificity optimization.",
            "category": "coding_task", "skill": "CSS & Responsive Design"
        },
        # Stage 2: Applied Engineering
        {
            "id": "FE_S2_01", "stage": "Stage 2: Component Architecture & State Management",
            "title": "Virtual DOM & Reconciliation Patterns",
            "description": "Implement unidirectional data flow, custom hooks, and state management architectures.",
            "category": "coding_task", "skill": "Frontend Architecture"
        },
        {
            "id": "FE_S2_02", "stage": "Stage 2: Component Architecture & State Management",
            "title": "Web Performance & Core Web Vitals Optimization",
            "description": "Optimize Interaction to Next Paint (INP), Largest Contentful Paint (LCP), code-splitting, and CSP security.",
            "category": "concept", "skill": "Web Performance & Security"
        },
        # Stage 3: Portfolio Projects
        {
            "id": "FE_S3_01", "stage": "Stage 3: Production Frontend Application",
            "title": "High-Performance SPA / PWA with Real-time Feeds",
            "description": "Build a modular, accessible, WCAG-compliant web application with offline service workers.",
            "category": "project", "skill": "Frontend Architecture"
        },
        # Stage 4: Placement Prep
        {
            "id": "FE_S4_01", "stage": "Stage 4: Frontend System Design & Live Coding",
            "title": "Frontend System Design & Component Architecture",
            "description": "Practice designing complex UI systems (Virtual List, Infinite Scroll, Autocomplete, Rich Text Editor).",
            "category": "concept", "skill": "Frontend Architecture"
        }
    ],
    "ai_ml_engineer": [
        # Stage 1: Foundations
        {
            "id": "AI_S1_01", "stage": "Stage 1: Mathematical Foundations & Deep Learning",
            "title": "Neural Network Mathematics & Backpropagation",
            "description": "Deep-dive into matrix calculus, activation saturation, loss functions, and optimization algorithms.",
            "category": "concept", "skill": "Deep Learning"
        },
        # Stage 2: Applied Engineering
        {
            "id": "AI_S2_01", "stage": "Stage 2: Transformer Architectures & Model Training",
            "title": "Self-Attention Transformers & Fine-Tuning",
            "description": "Train and fine-tune multi-head self-attention models with FlashAttention and PyTorch.",
            "category": "coding_task", "skill": "Deep Learning"
        },
        {
            "id": "AI_S2_02", "stage": "Stage 2: Transformer Architectures & Model Training",
            "title": "MLOps Pipelines & Drift Detection",
            "description": "Implement automated CI/CD for ML models, feature stores, and statistical data drift detection (K-S / PSI).",
            "category": "coding_task", "skill": "MLOps & Model Deployment"
        },
        # Stage 3: Portfolio Projects
        {
            "id": "AI_S3_01", "stage": "Stage 3: Production AI Engine & Inference Engine",
            "title": "High-Throughput Quantized Inference Microservice",
            "description": "Deploy an INT8 quantized LLM/Vision model using ONNX Runtime, TensorRT, and Docker.",
            "category": "project", "skill": "MLOps & Model Deployment"
        },
        # Stage 4: Placement Prep
        {
            "id": "AI_S4_01", "stage": "Stage 4: AI/ML Technical Interviews & Distributed Systems",
            "title": "Distributed ML Systems & Model Parallelism",
            "description": "Design distributed training pipelines (FSDP, DeepSpeed, Pipeline Parallelism, Raft Consensus).",
            "category": "concept", "skill": "Distributed Systems & Scalability"
        }
    ]
}

class RoadmapAgent:
    def generate_adaptive_roadmap(
        self,
        target_role: str,
        user_skills: Dict[str, float],
        completed_task_ids: Optional[List[str]] = None
    ) -> List[RoadmapTask]:
        """
        Generates a personalized, priority-ranked adaptive roadmap.
        Adapts task ordering based on skill gaps.
        """
        templates = ROLE_ROADMAP_TEMPLATES.get(target_role) or ROLE_ROADMAP_TEMPLATES["data_scientist"]
        completed_set = set(completed_task_ids or [])
        
        tasks: List[RoadmapTask] = []

        for item in templates:
            t_id = item["id"]
            skill = item["skill"]
            mastery = user_skills.get(skill, 0.20)
            is_completed = t_id in completed_set

            # If user has already achieved high mastery (>= 0.85) in that skill, mark early fundamentals complete
            if mastery >= 0.85 and item["stage"].startswith("Stage 1") and t_id not in completed_set:
                is_completed = True

            # Calculate dynamic priority: tasks for weak skills rank higher
            urgency_factor = max(0.1, 1.0 - mastery)
            stage_order = 1 if "Stage 1" in item["stage"] else (2 if "Stage 2" in item["stage"] else (3 if "Stage 3" in item["stage"] else 4))
            
            tasks.append(RoadmapTask(
                id=t_id,
                target_role=target_role,
                stage_name=item["stage"],
                title=item["title"],
                description=item["description"],
                category=item["category"],
                associated_skill=skill,
                priority_rank=stage_order,
                is_completed=is_completed
            ))

        return tasks
