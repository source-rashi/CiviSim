"""
reaction_predictor.py — Inference layer for the Random Forest surrogate model.

All PyTorch dependencies have been removed.  The model is now a scikit-learn
RandomForestRegressor, so inference is a single model.predict() call on a
normalised NumPy matrix.

Public API (unchanged):
    predict_batch(model, population, mean, std, policy_encoding)
        → List[Tuple[float, float, float]]

    predict_reaction(model, citizen, mean, std, policy_encoding)
        → Tuple[float, float, float]
"""

import logging
import numpy as np
from ai_models.training_model import apply_normalization

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Income scaling
# ---------------------------------------------------------------------------
# happiness_delta and support_delta live in [-1, 1].
# income_delta is a real rupee change — NOT clamped.
# The RF learns to predict in the same rupee range as the LLM training labels,
# so INCOME_SCALE stays 1.0 (no additional scaling needed).
# ---------------------------------------------------------------------------

INCOME_SCALE = 1.0


# ---------------------------------------------------------------------------
# Single citizen prediction
# ---------------------------------------------------------------------------

def predict_reaction(model, citizen, mean, std, policy_encoding):
    """
    Predict reaction for a single citizen.

    Returns:
        (happiness_delta, support_delta, income_delta)
        happiness_delta : float in [-1, 1]
        support_delta   : float in [-1, 1]
        income_delta    : float in rupees (can be large positive or negative)
    """
    features = _citizen_to_features(citizen, policy_encoding)
    features_norm = apply_normalization([features], mean, std)
    output = model.predict(features_norm)[0]   # shape (3,)
    return _scale_output(output)


# ---------------------------------------------------------------------------
# Batch prediction (primary call path — used by simulation_engine)
# ---------------------------------------------------------------------------

def predict_batch(model, population, mean, std, policy_encoding):
    """
    Predict reactions for an entire population in one vectorised call.

    Returns:
        List of tuples [(happiness_delta, support_delta, income_delta), ...]
    """
    if not population:
        logger.warning("predict_batch called with empty population.")
        return []

    # Build feature matrix for all citizens
    feature_matrix = [
        _citizen_to_features(c, policy_encoding) for c in population
    ]

    # Apply training normalisation — never recompute from this data
    features_norm = apply_normalization(feature_matrix, mean, std)

    # Single batch inference — RF processes all rows simultaneously
    outputs = model.predict(features_norm)          # shape (n, 3)

    results = [_scale_output(row) for row in outputs]

    logger.debug(
        "Batch prediction complete for %d citizens. "
        "Avg happiness_delta: %.3f  Avg income_delta: %.0f",
        len(population),
        np.mean([r[0] for r in results]),
        np.mean([r[2] for r in results]),
    )

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _citizen_to_features(citizen, policy_encoding):
    """
    Convert a citizen object into a 9-element feature vector.
    Must match the feature order used in create_training_data().

    Feature order:
        age, income, risk_tolerance, openness, political_leaning,
        policy_domain, policy_mechanism, policy_time_effect,
        affected_group_intensity
    """
    policy_vector = _normalize_policy_vector(policy_encoding)

    return [
        citizen.age,
        citizen.income,
        citizen.traits.get("risk_tolerance", 0.5),
        citizen.traits.get("openness", 0.5),
        citizen.traits.get("political_leaning", 0.5),
        *policy_vector,
    ]


def _normalize_policy_vector(policy_encoding):
    """Ensure predictor always receives a 4-value policy feature vector."""
    if isinstance(policy_encoding, (list, tuple, np.ndarray)):
        policy_vector = [float(v) for v in policy_encoding]
    elif policy_encoding is None:
        policy_vector = []
    else:
        policy_vector = [float(policy_encoding)]

    if len(policy_vector) < 4:
        policy_vector.extend([0.0] * (4 - len(policy_vector)))

    return policy_vector[:4]


def _scale_output(raw_output):
    """
    Scale raw model outputs into meaningful units.

        raw_output[0] → happiness_delta : clamped to [-1, 1]
        raw_output[1] → support_delta   : clamped to [-1, 1]
        raw_output[2] → income_delta    : scaled to rupees, NOT clamped

    The income output is intentionally left unclamped so that large
    positive or negative income effects are visible in the simulation.
    """
    happiness_delta = float(np.clip(raw_output[0], -1.0, 1.0))
    support_delta   = float(np.clip(raw_output[1], -1.0, 1.0))
    income_delta    = float(raw_output[2]) * INCOME_SCALE

    return (happiness_delta, support_delta, income_delta)