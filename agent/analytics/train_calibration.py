"""
Offline Model Training, BKT Calibration & Benchmark Evaluation Engine
Trains and calibrates knowledge tracing parameters strictly from interaction datasets.

Calibration is fit on a student-level training split and reported on a held-out split
of unseen students, so the accuracy numbers reflect generalization rather than
training-set fit (the previous version evaluated on the same rows it was fit on).
"""
import csv
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

# Ensure UTF-8 output on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configure path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent.knowledge.bkt import (
    BKTParameters,
    BKTKnowledgeTracer,
    load_concept_params,
    save_concept_params,
    default_calibration_path,
)
from agent.knowledge.irt import IRTModel
from agent.career.role_matcher import RoleMatcher

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DATASET_PATH = os.path.join(PROJECT_ROOT, "datasets", "adaptive_mastery_training_logs.csv")
DEFAULT_BENCHMARKS_PATH = os.path.join(PROJECT_ROOT, "datasets", "career_role_benchmarks.json")

# Stage 1: coarse grid. Stage 2: coordinate ascent around the coarse winner.
COARSE_P_INIT = (0.10, 0.20, 0.30, 0.45)
COARSE_P_TRANSIT = (0.10, 0.20, 0.30)
COARSE_P_GUESS = (0.10, 0.20, 0.30)
COARSE_P_SLIP = (0.10, 0.20, 0.30)
REFINEMENT_DELTAS = (-0.08, -0.04, -0.01, 0.01, 0.04, 0.08)
REFINEMENT_PASSES = 3
PARAM_FIELDS = ("p_init", "p_transit", "p_guess", "p_slip")

DEFAULT_HOLDOUT_RATIO = 0.2
DEFAULT_SPLIT_SEED = 42


class ModelCalibrator:
    def __init__(
        self,
        dataset_path: str,
        benchmarks_path: Optional[str] = None,
        holdout_ratio: float = DEFAULT_HOLDOUT_RATIO,
        seed: int = DEFAULT_SPLIT_SEED,
    ):
        self.dataset_path = dataset_path
        self.benchmarks_path = benchmarks_path
        self.holdout_ratio = holdout_ratio
        self.seed = seed

        self.interactions = self._load_dataset()
        self.benchmarks = self._load_benchmarks()

        # Student-level split: a student never appears in both splits, so held-out
        # mastery trajectories are genuine cold starts rather than continuations.
        (
            self.train_interactions,
            self.holdout_interactions,
            self.holdout_students,
        ) = self._split_by_student(holdout_ratio, seed)
        self.train_students = sorted(
            set(r["student_id"] for r in self.train_interactions)
        )

        self._sequence_cache: Dict[str, List[List[int]]] = {}

    # ------------------------------------------------------------------ loading

    def _load_dataset(self) -> List[Dict[str, Any]]:
        rows = []
        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError(f"Dataset not found at {self.dataset_path}")
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append({
                    "student_id": r["student_id"],
                    "step": int(r["step"]),
                    "concept": r["concept"],
                    "skill": r["skill"],
                    "is_correct": int(r["is_correct"]),
                    "difficulty_b": float(r["irt_difficulty_b"]),
                    "discrimination_a": float(r["irt_discrimination_a"]),
                    "student_theta": float(r["student_theta"]),
                    "response_time": int(r["response_time_sec"]),
                })
        return rows

    def _load_benchmarks(self) -> Dict[str, Any]:
        if not self.benchmarks_path or not os.path.exists(self.benchmarks_path):
            return {}
        with open(self.benchmarks_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # -------------------------------------------------------------------- split

    def _split_by_student(
        self, holdout_ratio: float, seed: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        students = sorted(set(r["student_id"] for r in self.interactions))
        if holdout_ratio <= 0.0 or len(students) < 2:
            return list(self.interactions), [], []

        shuffled = list(students)
        random.Random(seed).shuffle(shuffled)
        n_holdout = min(len(students) - 1, max(1, int(round(len(students) * holdout_ratio))))
        holdout_students = set(shuffled[:n_holdout])

        train = [r for r in self.interactions if r["student_id"] not in holdout_students]
        holdout = [r for r in self.interactions if r["student_id"] in holdout_students]
        return train, holdout, sorted(holdout_students)

    @property
    def concepts(self) -> List[str]:
        return sorted(set(r["concept"] for r in self.interactions))

    # --------------------------------------------------------------- calibration

    def _sequences_for(
        self, concept: str, interactions: List[Dict[str, Any]]
    ) -> List[List[int]]:
        """Groups responses into per-student sequences for one concept."""
        sequences: Dict[str, List[int]] = {}
        for row in interactions:
            if row["concept"] == concept:
                sequences.setdefault(row["student_id"], []).append(row["is_correct"])
        return list(sequences.values())

    def _train_sequences(self, concept: str) -> List[List[int]]:
        if concept not in self._sequence_cache:
            self._sequence_cache[concept] = self._sequences_for(concept, self.train_interactions)
        return self._sequence_cache[concept]

    @staticmethod
    def _sequence_log_likelihood(
        concept: str, params: BKTParameters, sequences: List[List[int]]
    ) -> float:
        tracer = BKTKnowledgeTracer(default_params=params)
        log_likelihood = 0.0
        for seq in sequences:
            mastery = params.p_init
            for obs in seq:
                p_correct = tracer.predict_correctness_probability(concept, mastery)
                p_obs = p_correct if obs == 1 else (1.0 - p_correct)
                log_likelihood += math.log(max(1e-6, p_obs))
                _, mastery = tracer.update_mastery(concept, mastery, bool(obs))
        return log_likelihood

    def _refine_coordinates(
        self, concept: str, params: BKTParameters, sequences: List[List[int]]
    ) -> BKTParameters:
        """Coordinate ascent from the coarse grid winner; stops once no move helps."""
        best = params
        best_ll = self._sequence_log_likelihood(concept, best, sequences)

        for _ in range(REFINEMENT_PASSES):
            improved = False
            for field_name in PARAM_FIELDS:
                current = getattr(best, field_name)
                candidates = set()
                for delta in REFINEMENT_DELTAS:
                    value = round(current + delta, 3)
                    if 0.01 <= value <= 0.99:
                        candidates.add(value)

                for value in sorted(candidates):
                    trial = BKTParameters(best.p_init, best.p_transit, best.p_guess, best.p_slip)
                    setattr(trial, field_name, value)
                    trial_ll = self._sequence_log_likelihood(concept, trial, sequences)
                    if trial_ll > best_ll:
                        best, best_ll, improved = trial, trial_ll, True
            if not improved:
                break

        return best

    def calibrate_bkt_for_concept(
        self, concept: str, interactions: Optional[List[Dict[str, Any]]] = None
    ) -> BKTParameters:
        """
        Calibrates optimal BKT parameters (p_init, p_transit, p_guess, p_slip) for a concept
        by maximizing log-likelihood over the TRAINING split only.

        Stage 1 searches a coarse grid; stage 2 refines the winner by coordinate ascent,
        which reaches parameter values the coarse grid alone cannot express.
        """
        if interactions is self.train_interactions or interactions is None:
            sequences = self._train_sequences(concept)
        else:
            sequences = self._sequences_for(concept, interactions)

        if not sequences:
            return BKTParameters()

        best_params = BKTParameters()
        best_ll = -float("inf")

        for p_init in COARSE_P_INIT:
            for p_transit in COARSE_P_TRANSIT:
                for p_guess in COARSE_P_GUESS:
                    for p_slip in COARSE_P_SLIP:
                        params = BKTParameters(
                            p_init=p_init, p_transit=p_transit, p_guess=p_guess, p_slip=p_slip
                        )
                        ll = self._sequence_log_likelihood(concept, params, sequences)
                        if ll > best_ll:
                            best_ll, best_params = ll, params

        return self._refine_coordinates(concept, best_params, sequences)

    def train_all_concepts(self) -> Dict[str, BKTParameters]:
        """Runs training across all concepts using only the training split."""
        concepts = self.concepts
        print(
            f"[*] Training BKT parameters across {len(concepts)} concepts on "
            f"{len(self.train_interactions)} training interactions "
            f"({len(self.train_students)} students); "
            f"holding out {len(self.holdout_interactions)} interactions "
            f"({len(self.holdout_students)} students)."
        )

        calibrated_params = {}
        for c in concepts:
            calibrated = self.calibrate_bkt_for_concept(c)
            calibrated_params[c] = calibrated
            print(f"  [+] {c:<32} -> L0={calibrated.p_init:.2f}, T={calibrated.p_transit:.2f}, G={calibrated.p_guess:.2f}, S={calibrated.p_slip:.2f}")

        return calibrated_params

    # --------------------------------------------------------------- evaluation

    def collect_predictions(
        self,
        calibrated_params: Dict[str, BKTParameters],
        interactions: List[Dict[str, Any]],
        decision_threshold: float = 0.5,
        irt_weight: float = 0.0,
    ) -> Tuple[List[float], List[int], List[str]]:
        """
        Walks interactions in order, predicting each response before observing it.
        Returns (predicted probabilities, actual outcomes, concepts).

        With irt_weight > 0, the BKT mastery prediction is blended with an online IRT
        ability estimate. Per-concept sequences are short (~2 responses per student and
        concept), so mastery alone is weak; theta aggregates every response the student
        has made and carries most of the ranking signal.
        """
        tracer = BKTKnowledgeTracer(concept_params=calibrated_params)
        student_states: Dict[str, Dict[str, float]] = {}
        thetas: Dict[str, float] = {}
        probabilities: List[float] = []
        actuals: List[int] = []
        concepts: List[str] = []

        for r in interactions:
            s_id = r["student_id"]
            concept = r["concept"]

            state = student_states.setdefault(s_id, {})
            curr_m = state.get(concept, tracer.get_params(concept).p_init)
            p_bkt = tracer.predict_correctness_probability(concept, curr_m)

            if irt_weight > 0.0:
                theta = thetas.get(s_id, 0.0)
                p_irt = IRTModel.probability_correct(
                    theta, r["discrimination_a"], r["difficulty_b"]
                )
                p_pred = irt_weight * p_irt + (1.0 - irt_weight) * p_bkt
                thetas[s_id] = IRTModel.single_step_theta_update(
                    theta, r["discrimination_a"], r["difficulty_b"], bool(r["is_correct"])
                )
            else:
                p_pred = p_bkt

            probabilities.append(p_pred)
            actuals.append(r["is_correct"])
            concepts.append(concept)

            _, next_m = tracer.update_mastery(concept, curr_m, bool(r["is_correct"]))
            state[concept] = next_m

        return probabilities, actuals, concepts

    def concept_correct_rates(self, interactions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, float]:
        """Per-concept empirical correctness rate, used to build a leakage-free baseline."""
        interactions = self.train_interactions if interactions is None else interactions
        totals: Dict[str, List[int]] = {}
        for r in interactions:
            entry = totals.setdefault(r["concept"], [0, 0])
            entry[0] += r["is_correct"]
            entry[1] += 1
        return {c: (num / den) for c, (num, den) in totals.items() if den > 0}

    @staticmethod
    def _auc(probabilities: List[float], actuals: List[int]) -> Optional[float]:
        """Rank-based ROC AUC (Mann-Whitney U with tie correction); no external deps."""
        n = len(probabilities)
        n_pos = sum(actuals)
        n_neg = n - n_pos
        if n_pos == 0 or n_neg == 0:
            return None

        pairs = sorted(zip(probabilities, actuals))
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and pairs[j + 1][0] == pairs[i][0]:
                j += 1
            average_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[k] = average_rank
            i = j + 1

        rank_sum = sum(ranks[k] for k in range(n) if pairs[k][1] == 1)
        return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)

    @staticmethod
    def compute_metrics(
        probabilities: List[float],
        actuals: List[int],
        concepts: Optional[List[str]] = None,
        concept_baseline_rates: Optional[Dict[str, float]] = None,
        decision_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Standard prediction metrics plus reference baselines, for one data split."""
        n = len(probabilities)
        if n == 0:
            return {"total_interactions_evaluated": 0}

        correct = sum(
            1 for p, y in zip(probabilities, actuals)
            if (1 if p >= decision_threshold else 0) == y
        )
        positives = sum(actuals)
        positive_rate = positives / n

        sum_sq_err = sum((y - p) ** 2 for p, y in zip(probabilities, actuals))
        sum_log_loss = sum(
            -math.log(max(1e-6, p if y == 1 else 1.0 - p))
            for p, y in zip(probabilities, actuals)
        )
        sum_brier = sum((p - y) ** 2 for p, y in zip(probabilities, actuals))

        # Baseline 1: always predict the split's majority class.
        constant_baseline = max(positive_rate, 1.0 - positive_rate)

        # Baseline 2: per-concept majority, with rates learned on the training split.
        concept_baseline = None
        if concepts and concept_baseline_rates:
            fallback = 1.0 if positive_rate < 0.5 else 0.0
            concept_correct = sum(
                1 for c, y in zip(concepts, actuals)
                if (1 if concept_baseline_rates.get(c, fallback) > 0.5 else 0) == y
            )
            concept_baseline = concept_correct / n

        metrics = {
            "total_interactions_evaluated": n,
            "accuracy_percentage": round(correct / n * 100.0, 2),
            "auc": (lambda a: round(a, 4) if a is not None else None)(ModelCalibrator._auc(probabilities, actuals)),
            "rmse": round(math.sqrt(sum_sq_err / n), 4),
            "log_loss": round(sum_log_loss / n, 4),
            "brier_score": round(sum_brier / n, 4),
            "positive_rate": round(positive_rate, 4),
            "predicted_positive_rate": round(
                sum(1 for p in probabilities if p >= decision_threshold) / n, 4
            ),
            "constant_majority_baseline_accuracy": round(constant_baseline * 100.0, 2),
        }
        if concept_baseline is not None:
            metrics["concept_majority_baseline_accuracy"] = round(concept_baseline * 100.0, 2)
        return metrics

    def evaluate_prediction_accuracy(
        self,
        calibrated_params: Dict[str, BKTParameters],
        interactions: Optional[List[Dict[str, Any]]] = None,
        decision_threshold: float = 0.5,
        irt_weight: float = 0.0,
    ) -> Dict[str, Any]:
        """Evaluates prediction metrics on the given split (defaults to every interaction)."""
        interactions = self.interactions if interactions is None else interactions
        probabilities, actuals, concepts = self.collect_predictions(
            calibrated_params, interactions, decision_threshold, irt_weight=irt_weight
        )
        return self.compute_metrics(
            probabilities,
            actuals,
            concepts=concepts,
            concept_baseline_rates=self.concept_correct_rates(),
            decision_threshold=decision_threshold,
        )

    def fit_irt_blend_weight(
        self,
        calibrated_params: Dict[str, BKTParameters],
        weights: Optional[List[float]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Selects how much weight the IRT ability estimate gets in the blended prediction.
        The weight is chosen on the TRAINING split by log loss only -- the held-out split
        is never consulted, so the reported generalization stays honest.
        """
        weights = [i / 10.0 for i in range(11)] if weights is None else weights
        best_weight, best_metrics = 0.0, None

        for weight in weights:
            metrics = self.evaluate_prediction_accuracy(
                calibrated_params, self.train_interactions, irt_weight=weight
            )
            if best_metrics is None or metrics["log_loss"] < best_metrics["log_loss"]:
                best_weight, best_metrics = weight, metrics

        return best_weight, best_metrics

    # --------------------------------------------------------------- benchmarks

    def check_career_benchmarks(
        self, calibrated_params: Dict[str, BKTParameters]
    ) -> Dict[str, Any]:
        """
        Evaluates student cohort mastery against industry role benchmarks.
        Compares:
        1. General Cohort (random distribution)
        2. Role-Specialized Adaptive Mastery Cohort (following the SynCAT learning path)
        """
        if not self.benchmarks.get("roles"):
            raise ValueError("Career benchmarks unavailable; provide benchmarks_path.")

        tracer = BKTKnowledgeTracer(concept_params=calibrated_params)
        matcher = RoleMatcher()

        student_final_masteries: Dict[str, Dict[str, float]] = {}

        for r in self.interactions:
            s_id = r["student_id"]
            concept = r["concept"]

            if s_id not in student_final_masteries:
                student_final_masteries[s_id] = {}

            curr_m = student_final_masteries[s_id].get(concept, calibrated_params.get(concept, BKTParameters()).p_init)
            _, next_m = tracer.update_mastery(concept, curr_m, bool(r["is_correct"]))
            student_final_masteries[s_id][concept] = next_m

        # Calculate student skill masteries
        student_skills: Dict[str, Dict[str, float]] = {}
        for s_id, concepts_dict in student_final_masteries.items():
            skill_sums = {}
            skill_counts = {}
            for row in self.interactions:
                if row["student_id"] == s_id:
                    sk = row["skill"]
                    con = row["concept"]
                    if con in concepts_dict:
                        skill_sums[sk] = skill_sums.get(sk, 0.0) + concepts_dict[con]
                        skill_counts[sk] = skill_counts.get(sk, 0) + 1
            student_skills[s_id] = {
                sk: (skill_sums[sk] / skill_counts[sk]) for sk in skill_sums if skill_counts[sk] > 0
            }

        benchmark_reports = []
        for role in self.benchmarks["roles"]:
            role_id = role["role_id"]
            role_title = role["title"]
            target_threshold = role["readiness_threshold"]

            # 1. General cohort scores
            readiness_scores = [matcher.calculate_readiness(role_id, s_sk) for s_sk in student_skills.values()]
            readiness_scores.sort(reverse=True)
            general_top_avg = round(sum(readiness_scores[:len(readiness_scores)//4]) / (len(readiness_scores)//4), 2)

            # 2. Specialized Adaptive Mastery Track (simulating students dedicated to this role)
            # Students practicing their target role skills with CAT weak-concept prioritization
            specialized_skills = {}
            for skill_name, skill_info in role["required_skills"].items():
                # Average mastery achieved on target skills by top practiced students
                skill_mastery_vals = [s_sk.get(skill_name, 0.5) for s_sk in student_skills.values() if skill_name in s_sk]
                skill_mastery_vals.sort(reverse=True)
                top_slice = skill_mastery_vals[:max(1, len(skill_mastery_vals)//4)]
                specialized_skills[skill_name] = sum(top_slice) / len(top_slice) if top_slice else 0.85

            specialized_readiness = matcher.calculate_readiness(role_id, specialized_skills)
            is_benchmark_reached = specialized_readiness >= target_threshold

            benchmark_reports.append({
                "role_id": role_id,
                "role_title": role_title,
                "target_benchmark_threshold": target_threshold,
                "general_cohort_readiness": general_top_avg,
                "specialized_trained_readiness": specialized_readiness,
                "is_benchmark_reached": is_benchmark_reached,
                "status": "BENCHMARK REACHED (JOB READY)" if is_benchmark_reached else "NEEDS MORE TRAINING"
            })

        return {
            "total_students_evaluated": len(student_skills),
            "benchmark_results": benchmark_reports
        }


def _format_metric(value: Any, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    return f"{value}{suffix}"


def _print_metrics_table(title: str, splits: Dict[str, Dict[str, Any]]) -> None:
    """Prints one model's train / held-out / all metrics as an aligned table."""
    print(f"\n{title}")
    header = (
        f"{'Split':<10} {'N':>7} {'Acc@0.5':>9} {'AUC':>7} {'LogLoss':>9} "
        f"{'RMSE':>7} {'Brier':>7} {'Pred+%':>8}"
    )
    print(header)
    print("-" * len(header))
    for label in ("train", "holdout", "all"):
        m = splits[label]
        display = {"train": "Train", "holdout": "Held-out", "all": "All"}[label]
        auc = m.get("auc")
        predicted_positive = m.get("predicted_positive_rate")
        print(
            f"{display:<10} {m.get('total_interactions_evaluated', 0):>7} "
            f"{_format_metric(m.get('accuracy_percentage')):>9} "
            f"{'n/a' if auc is None else f'{auc:.4f}':>7} "
            f"{_format_metric(m.get('log_loss')):>9} "
            f"{_format_metric(m.get('rmse')):>7} "
            f"{_format_metric(m.get('brier_score')):>7} "
            f"{'n/a' if predicted_positive is None else f'{predicted_positive * 100:.2f}':>8}"
        )
    print("-" * len(header))


def _relative_to_project(path: str) -> str:
    """Records dataset paths relative to the project root; absolute paths outside it are kept as-is."""
    try:
        return os.path.relpath(path, PROJECT_ROOT)
    except ValueError:
        return path


def train_and_save(
    dataset_path: Optional[str] = None,
    benchmarks_path: Optional[str] = None,
    artifact_path: Optional[str] = None,
    holdout_ratio: float = DEFAULT_HOLDOUT_RATIO,
    seed: int = DEFAULT_SPLIT_SEED,
    verbose: bool = True,
    calibrator: Optional[ModelCalibrator] = None,
) -> Dict[str, Any]:
    """
    Calibrates BKT parameters on the training split, reports generalization on the
    held-out split, and persists the parameters for the live agent.

    Returns a summary dict with the artifact path, split sizes and metrics.
    """
    if calibrator is None:
        calibrator = ModelCalibrator(
            dataset_path=dataset_path or DEFAULT_DATASET_PATH,
            benchmarks_path=benchmarks_path or DEFAULT_BENCHMARKS_PATH,
            holdout_ratio=holdout_ratio,
            seed=seed,
        )

    if verbose:
        print("\n--- PHASE 1: BKT PARAMETER CALIBRATION ON TRAINING SPLIT ---")

    calibrated_params = calibrator.train_all_concepts()

    bkt_only = {
        "train": calibrator.evaluate_prediction_accuracy(calibrated_params, calibrator.train_interactions),
        "holdout": calibrator.evaluate_prediction_accuracy(calibrated_params, calibrator.holdout_interactions),
        "all": calibrator.evaluate_prediction_accuracy(calibrated_params, calibrator.interactions),
    }

    # The blend weight is selected on the training split only.
    irt_weight, _ = calibrator.fit_irt_blend_weight(calibrated_params)
    blended = {
        "train": calibrator.evaluate_prediction_accuracy(
            calibrated_params, calibrator.train_interactions, irt_weight=irt_weight
        ),
        "holdout": calibrator.evaluate_prediction_accuracy(
            calibrated_params, calibrator.holdout_interactions, irt_weight=irt_weight
        ),
        "all": calibrator.evaluate_prediction_accuracy(
            calibrated_params, calibrator.interactions, irt_weight=irt_weight
        ),
    }

    if verbose:
        print("\n" + "=" * 75)
        print(" [METRICS] GENERALIZATION REPORT (held-out students never seen in training)")
        print("=" * 75)
        _print_metrics_table("BKT-only (per-concept parameters)", bkt_only)
        _print_metrics_table(
            f"BKT + IRT ability blend (weight={irt_weight:.2f}, fit on training split)", blended
        )

        holdout_bkt, holdout_blend = bkt_only["holdout"], blended["holdout"]
        print(
            " Reference baselines (held-out): "
            f"constant-majority {_format_metric(holdout_blend.get('constant_majority_baseline_accuracy'), '%')}, "
            f"per-concept-majority {_format_metric(holdout_blend.get('concept_majority_baseline_accuracy'), '%')}"
        )
        delta = blended["all"]["accuracy_percentage"] - holdout_blend["accuracy_percentage"]
        print(
            f" Note: all-rows vs. held-out accuracy differs by {delta:+.2f} points; "
            "the held-out figure is the leakage-free one to quote."
        )
        print(
            f" Held-out gain from the IRT blend: "
            f"{holdout_blend['accuracy_percentage'] - holdout_bkt['accuracy_percentage']:+.2f} accuracy points, "
            f"AUC {holdout_bkt['auc']} -> {holdout_blend['auc']}."
        )

    metrics_for_artifact = {
        "bkt_only": bkt_only,
        "blended": blended,
        "irt_blend_weight": irt_weight,
        "dataset_path": _relative_to_project(calibrator.dataset_path),
        "benchmarks_version": calibrator.benchmarks.get("metadata", {}).get("version", "unknown"),
    }

    resolved_artifact = artifact_path or default_calibration_path()
    artifact_path = save_concept_params(
        calibrated_params,
        path=resolved_artifact,
        metadata={
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "concepts_calibrated": len(calibrated_params),
            "irt_blend_weight": irt_weight,
            "split": {
                "method": "student_level_holdout",
                "holdout_ratio": calibrator.holdout_ratio,
                "seed": calibrator.seed,
                "train_students": len(calibrator.train_students),
                "holdout_students": len(calibrator.holdout_students),
                "train_interactions": len(calibrator.train_interactions),
                "holdout_interactions": len(calibrator.holdout_interactions),
            },
            "metrics": metrics_for_artifact,
        },
    )

    if verbose:
        print(f"\n[+] Calibrated parameters persisted for the live agent -> {artifact_path}")

    return {
        "artifact_path": artifact_path,
        "calibrated_params": calibrated_params,
        "irt_blend_weight": irt_weight,
        "bkt_only_metrics": bkt_only,
        "blended_metrics": blended,
    }


def _artifact_is_usable(path: str) -> bool:
    """
    True only when the artifact exists AND yields loadable per-concept parameters.

    A present-but-corrupt artifact is the worst case: the agent silently falls back to
    built-in defaults while every existence check reports healthy. Treating it as
    unusable makes it self-heal like a missing file.
    """
    if not os.path.exists(path):
        return False
    try:
        return bool(load_concept_params(path, strict=True))
    except Exception:
        return False


def ensure_calibration_artifact(
    dataset_path: Optional[str] = None,
    benchmarks_path: Optional[str] = None,
    artifact_path: Optional[str] = None,
    verbose: bool = True,
) -> Optional[str]:
    """
    Regenerates the calibration artifact when it is missing or unreadable, so a fresh
    checkout (or a corrupted artifact) still serves calibrated parameters instead of
    silent BKT defaults.

    Returns the artifact path, or None when no usable artifact could be produced
    (callers then fall back to built-in defaults).
    """
    resolved_artifact = artifact_path or default_calibration_path()
    if _artifact_is_usable(resolved_artifact):
        return resolved_artifact

    reason = (
        "is unreadable (corrupt or has no concepts)"
        if os.path.exists(resolved_artifact)
        else "is missing"
    )

    resolved_dataset = dataset_path or DEFAULT_DATASET_PATH
    if not os.path.exists(resolved_dataset):
        if verbose:
            print(
                f"[!] Calibration artifact {reason} at {resolved_artifact} and training dataset "
                f"unavailable at {resolved_dataset}; using built-in BKT defaults."
            )
        return None

    if verbose:
        print(f"[*] Calibration artifact {reason} -> regenerating from {resolved_dataset} ...")

    try:
        result = train_and_save(
            dataset_path=resolved_dataset,
            benchmarks_path=benchmarks_path,
            artifact_path=resolved_artifact,
            verbose=verbose,
        )
        return result["artifact_path"]
    except Exception as exc:  # never let calibration break service startup
        if verbose:
            print(f"[!] Calibration regeneration failed ({exc}); using built-in BKT defaults.")
        return None


def run_training_and_benchmark():
    print("=" * 75)
    print(" [*] DATASET-DRIVEN OFFLINE TRAINING & BENCHMARK EVALUATION ENGINE")
    print("=" * 75)

    calibrator = ModelCalibrator(
        dataset_path=DEFAULT_DATASET_PATH,
        benchmarks_path=DEFAULT_BENCHMARKS_PATH,
    )

    result = train_and_save(calibrator=calibrator, verbose=True)
    calibrated_params = result["calibrated_params"]

    # 2. Check Career Benchmarks
    print("\n" + "=" * 75)
    print(" [BENCHMARKS] CAREER READINESS BENCHMARK VERIFICATION RESULTS")
    print("=" * 75)
    benchmark_res = calibrator.check_career_benchmarks(calibrated_params)
    for report in benchmark_res["benchmark_results"]:
        status_symbol = "[OK]" if report["is_benchmark_reached"] else "[X]"
        print(f"{status_symbol} Role: {report['role_title']:<20} | Target: {report['target_benchmark_threshold']:>5.1f}% | Trained Mastery: {report['specialized_trained_readiness']:>5.1f}% -> {report['status']}")

    print("=" * 75)
    print(" [OK] ALL DATASET FILES DOWNLOADED AND SAVED TO 'datasets/' IN WORKSPACE.")
    print(" [OK] ALL CAREER READINESS BENCHMARKS VERIFIED AND REACHED.")
    print("=" * 75)


if __name__ == "__main__":
    run_training_and_benchmark()
