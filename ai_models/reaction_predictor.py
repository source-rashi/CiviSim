import torch
import numpy as np
import logging
from ai_models.training_model import apply_normalization

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Income scaling
# ---------------------------------------------------------------------------
# happiness_delta and support_delta live in [-1, 1] — they are scores.
# income_delta is a real rupee change — it should NOT be clamped to [-1, 1].
# The model outputs a raw float for income; we scale it to a realistic range.
#
# INCOME_SCALE: multiply the raw model output by this to get rupees.
# Tune this based on your LLM reactions — if Gemini says income_change
# is typically in the range [-5000, +20000], set this to 10000.
# ---------------------------------------------------------------------------

INCOME_SCALE = 10_000  # rupees per unit of raw model output


# ---------------------------------------------------------------------------
# Single citizen prediction
# ---------------------------------------------------------------------------

def predict_reaction(model, citizen, mean, std, policy_encoding):
    """
    Predict reaction for a single citizen.

    Returns a tuple: (happiness_delta, support_delta, income_delta)
        happiness_delta : float in [-1, 1]
        support_delta   : float in [-1, 1]
        income_delta    : float in rupees (can be large positive or negative)
    """
    features = _citizen_to_features(citizen, policy_encoding)
    features_norm = apply_normalization([features], mean, std)

    model.eval()
    with torch.no_grad():
        x = torch.tensor(features_norm, dtype=torch.float32)
        output = model(x).numpy()[0]

    return _scale_output(output)


# ---------------------------------------------------------------------------
# Batch prediction
# ---------------------------------------------------------------------------

def predict_batch(model, population, mean, std, policy_encoding):
    """
    Predict reactions for an entire population in one forward pass.
    Much faster than calling predict_reaction() in a loop.

    Returns a list of tuples: [(happiness_delta, support_delta, income_delta), ...]
    """
    if not population:
        logger.warning("predict_batch called with empty population.")
        return []

    # Build feature matrix for all citizens
    feature_matrix = [
        _citizen_to_features(c, policy_encoding) for c in population
    ]

    # Apply training normalization — never recompute from this data
    features_norm = apply_normalization(feature_matrix, mean, std)

    model.eval()
    with torch.no_grad():
        x = torch.tensor(features_norm, dtype=torch.float32)
        outputs = model(x).numpy()

    results = [_scale_output(row) for row in outputs]

    logger.debug(
        f"Batch prediction complete for {len(population)} citizens. "
        f"Avg happiness_delta: {np.mean([r[0] for r in results]):.3f}, "
        f"Avg income_delta: {np.mean([r[2] for r in results]):,.0f}"
    )

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _citizen_to_features(citizen, policy_encoding):
    """
    Convert a citizen object into a 6-element feature vector.
    Must match the feature order used in create_training_data().
    """
    return [
        citizen.age,
        citizen.income,
        citizen.traits.get("risk_tolerance", 0.5),
        citizen.traits.get("openness", 0.5),
        citizen.traits.get("political_leaning", 0.5),
        policy_encoding,
    ]


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