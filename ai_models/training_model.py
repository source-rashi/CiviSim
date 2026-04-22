"""
training_model.py — Random Forest surrogate for citizen reaction prediction.

WHY RANDOM FOREST OVER PYTORCH:
  The previous architecture (9 → 64 → 32 → 16 → 3 PyTorch network) was
  trained on ~200 LLM-labelled samples.  That network had ~6,000 trainable
  parameters for 200 rows — a guaranteed overfit.  Random Forest dominates
  tabular data in low-n regimes:
    • No gradient descent, no overfit spiral.
    • Naturally handles multi-output regression.
    • Trains in <0.1 s on 200 rows.
    • Feature importance is interpretable — a bonus for government demos.

WhY NOT LightGBM here:
  LightGBM shines at n > 5,000.  At n = 200 you need careful `num_leaves`
  tuning to prevent collapse to a constant.  RF just works out of the box.

PUBLIC API (unchanged — all callers are still compatible):
  train_model(X, y, ...) → (model, mean, std, diagnostics)
  create_training_data(population, llm_results, policy) → (X, y)
  encode_policy(policy) → List[float]
  apply_normalization(X, mean, std) → np.ndarray
  normalize_features(X) → (np.ndarray, mean, std)
"""

import logging
import random
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature normalization  (mean/std kept for inference compatibility)
# ---------------------------------------------------------------------------

def normalize_features(X: List[List[float]]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Normalise feature matrix using mean/std.

    The mean and std MUST be stored and reused for every inference call.
    Never recompute from eval data.

    NOTE: RF does not require normalisation for correctness, but we keep
    normalisation so that the rest of the pipeline (reaction_predictor.py)
    does not need to change.  It also makes the stored diagnostics comparable
    across runs.
    """
    X_arr = np.array(X, dtype=np.float32)
    mean = X_arr.mean(axis=0)
    std = X_arr.std(axis=0) + 1e-8
    X_norm = (X_arr - mean) / std
    return X_norm, mean, std


def apply_normalization(
    X: List[List[float]],
    mean: np.ndarray,
    std: np.ndarray,
) -> np.ndarray:
    """
    Apply pre-computed normalisation to new (inference-time) data.
    Always use the mean/std returned by train_model — never recompute.
    """
    X_arr = np.array(X, dtype=np.float32)
    return (X_arr - mean) / (std + 1e-8)


# ---------------------------------------------------------------------------
# Policy encoding
# ---------------------------------------------------------------------------

DOMAIN_MAP: Dict[str, int] = {
    "education":   0,
    "tax":         1,
    "agriculture": 2,
    "health":      3,
    "general":     4,
}

MECHANISM_MAP: Dict[str, int] = {
    "subsidy":     0,
    "tax_change":  1,
    "regulation":  2,
    "restriction": 3,
    "investment":  4,
    "reform":      5,
    "general":     6,
}

TIME_EFFECT_MAP: Dict[str, int] = {
    "immediate": 0,
    "gradual":   1,
    "long_term": 2,
}

MAX_AFFECTED_GROUPS = 8.0


def _normalize_lookup(mapping: Dict[str, int], key: str, fallback: str = "general") -> float:
    max_index = max(mapping.values()) if mapping else 1
    mapped = mapping.get(str(key).strip().lower(), mapping.get(fallback, max_index))
    return float(mapped) / float(max(max_index, 1))


def encode_policy(policy: Optional[Dict[str, Any]]) -> List[float]:
    """
    Return normalised policy features for model conditioning.

    Feature order:
      1) domain score          (0–1)
      2) mechanism score       (0–1)
      3) time-effect score     (0–1)
      4) affected-group count  (0–1, capped at 8)
    """
    policy_obj = policy or {}
    domain = policy_obj.get("domain", "general")
    mechanism = policy_obj.get("mechanism", "general")
    time_effect = policy_obj.get("time_effect", "gradual")
    affected_groups = policy_obj.get("affected_groups", [])
    affected_count = len(affected_groups) if isinstance(affected_groups, list) else 0

    return [
        _normalize_lookup(DOMAIN_MAP, domain),
        _normalize_lookup(MECHANISM_MAP, mechanism),
        _normalize_lookup(TIME_EFFECT_MAP, time_effect, fallback="gradual"),
        min(float(affected_count), MAX_AFFECTED_GROUPS) / MAX_AFFECTED_GROUPS,
    ]


# ---------------------------------------------------------------------------
# Training data assembly
# ---------------------------------------------------------------------------

def create_training_data(
    population: list,
    llm_results: List[Dict[str, Any]],
    policy: Optional[Dict[str, Any]] = None,
) -> Tuple[List[List[float]], List[List[float]]]:
    """
    Build (X, y) arrays from citizen profiles and LLM reactions.

    Features (9-D):
        age, income, risk_tolerance, openness, political_leaning,
        policy_domain, policy_mechanism, policy_time_effect,
        affected_group_intensity

    Targets (3-D):
        happiness_change, support_change, income_change
    """
    policy_features = encode_policy(policy)
    X: List[List[float]] = []
    y: List[List[float]] = []

    for citizen, result in zip(population, llm_results):
        features = [
            citizen.age,
            citizen.income,
            citizen.traits.get("risk_tolerance", 0.5),
            citizen.traits.get("openness", 0.5),
            citizen.traits.get("political_leaning", 0.5),
            *policy_features,
        ]
        targets = [
            float(result.get("happiness_change", 0.0)),
            float(result.get("support_change", 0.0)),
            float(result.get("income_change", 0.0)),
        ]
        X.append(features)
        y.append(targets)

    return X, y


# ---------------------------------------------------------------------------
# Model training — Random Forest
# ---------------------------------------------------------------------------

def train_model(
    X: List[List[float]],
    y: List[List[float]],
    *,
    # kwargs kept for callers that pass these — all are safe to accept and ignore
    epochs: int = 0,
    validation_split: float = 0.2,
    return_metrics: bool = False,
    batch_size: int = 32,
    seed: Optional[int] = None,
    early_stopping_patience: int = 0,
    min_delta: float = 0.0,
    **_kwargs: Any,
) -> Any:
    """
    Train a Random Forest multi-output regressor on (X, y).

    Returns:
        (model, mean, std)              when return_metrics=False
        (model, mean, std, diagnostics) when return_metrics=True

    The returned mean and std MUST be passed to apply_normalization()
    at inference time (reaction_predictor.predict_batch).

    Hyperparameter rationale for n ≈ 200:
        n_estimators=300   — enough trees to stabilise variance; cheap at this n.
        min_samples_leaf=2 — stops leaves from holding a single sample (overfit guard).
        max_features='sqrt'— classic Breiman recommendation; keeps trees decorrelated.
        bootstrap=True     — enables out-of-bag (OOB) error estimate at zero cost.
        random_state=seed  — reproducibility.
    """
    rng_seed = int(seed) if seed is not None else None
    if rng_seed is not None:
        random.seed(rng_seed)
        np.random.seed(rng_seed % (2 ** 32 - 1))

    X_norm, mean, std = normalize_features(X)
    y_arr = np.array(y, dtype=np.float32)

    n_samples = len(X_norm)
    if n_samples == 0:
        raise ValueError("Cannot train model with empty training data.")

    # ---- train/val split (stratification not needed for RF, but we keep
    #      diagnostics identical so meta_agent thresholds still apply)
    val_frac = max(0.0, min(0.5, float(validation_split)))
    do_val = n_samples >= 10 and val_frac > 0.0

    if do_val:
        X_train, X_val, y_train, y_val = train_test_split(
            X_norm, y_arr,
            test_size=val_frac,
            random_state=rng_seed,
        )
    else:
        X_train, y_train = X_norm, y_arr
        X_val, y_val = None, None

    # ---- build and train RF ------------------------------------------------
    model = RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        max_features="sqrt",
        bootstrap=True,
        oob_score=True,     # free OOB error estimate
        n_jobs=-1,          # use all cores
        random_state=rng_seed,
    )
    model.fit(X_train, y_train)

    # ---- diagnostics -------------------------------------------------------
    train_preds = model.predict(X_train)
    train_mae = float(mean_absolute_error(y_train, train_preds))

    val_mae: Optional[float] = None
    if X_val is not None and y_val is not None:
        val_preds = model.predict(X_val)
        val_mae = float(mean_absolute_error(y_val, val_preds))

    oob_score = float(model.oob_score_) if hasattr(model, "oob_score_") else None

    diagnostics: Dict[str, Any] = {
        "samples_total":        int(n_samples),
        "samples_train":        int(len(X_train)),
        "samples_validation":   int(len(X_val)) if X_val is not None else 0,
        "train_mae":            round(train_mae, 6),
        "validation_mae":       round(val_mae, 6) if val_mae is not None else None,
        "oob_score":            round(oob_score, 6) if oob_score is not None else None,
        # kept for meta_agent compatibility
        "epochs_requested":     0,
        "epochs_completed":     1,
        "early_stopped":        False,
        "best_epoch":           1,
        "effective_batch_size": int(n_samples),
        "random_seed":          rng_seed,
        "train_validation_mae_gap": (
            round(abs(train_mae - val_mae), 6) if val_mae is not None else None
        ),
        "model_type":           "RandomForestRegressor",
        "n_estimators":         300,
    }

    logger.info(
        "RF training complete. train_mae=%.4f  val_mae=%s  oob_score=%s  n=%d",
        train_mae,
        f"{val_mae:.4f}" if val_mae is not None else "n/a",
        f"{oob_score:.4f}" if oob_score is not None else "n/a",
        n_samples,
    )

    if return_metrics:
        return model, mean, std, diagnostics
    return model, mean, std


# ---------------------------------------------------------------------------
# Evaluation helper (kept for compatibility)
# ---------------------------------------------------------------------------

def evaluate_model(
    model: Any,
    X: List[List[float]],
    y: List[List[float]],
    train_mean: np.ndarray,
    train_std: np.ndarray,
) -> float:
    """
    Evaluate model on held-out data using the training normalisation.
    Always pass mean/std from train_model — never recompute from eval data.
    """
    X_norm = apply_normalization(X, train_mean, train_std)
    y_arr = np.array(y, dtype=np.float32)

    preds = model.predict(X_norm)
    mae = float(mean_absolute_error(y_arr, preds))
    logger.info("Evaluation MAE: %.6f", mae)
    return mae