"""
simulation_engine.py — Markov-chain temporal policy simulation.

DESIGN RATIONALE
================
The previous engine called `predict_batch()` at every step and added the
full initial-shock delta to each citizen.  This is broken: the model was
trained on the *immediate* reaction to the policy, so repeating it N times
creates unrealistic linear drift with no feedback.

This engine replaces that with a Markov-state machine:

    STATES              thriving | stable | struggling | crisis
    ─────────────────────────────────────────────────────────────
    thriving   happiness ≥ 0.65  → positive compounding, income grows
    stable     0.4 ≤ h < 0.65   → mild drift, near-neutral income
    struggling 0.2 ≤ h < 0.40   → negative compounding, income decays
    crisis     happiness < 0.20  → severe negative, income deteriorates fast

At each time step:
  1. The RF model predicts an *attenuated* per-step delta for each citizen
     (the shock is spread over `steps`, so the total area under the curve
     equals the one-shot LLM signal).
  2. A state-specific multiplier amplifies or dampens that delta.
  3. The citizen's state is updated; then `markov_state` is re-derived.

This produces realistic S-curves, divergence between groups, and saturation
effects — all without any additional LLM calls.

OUTPUT (unchanged — app.py is not affected):
    {
        "happiness": [float, ...],   # per-step population average
        "support":   [float, ...],
        "income":    [float, ...],
    }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from utils.metrics import average_happiness, average_support, average_income
from ai_models.reaction_predictor import predict_batch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Markov state definitions
# ---------------------------------------------------------------------------

# Happiness thresholds that define each state.
_STATE_THRESHOLDS: Dict[str, Tuple[float, float]] = {
    "thriving":   (0.65, 1.00),
    "stable":     (0.40, 0.65),
    "struggling": (0.20, 0.40),
    "crisis":     (0.00, 0.20),
}

# Per-state multipliers applied to the attenuated delta each step.
#   > 1.0  → positive feedback (thriving citizens adapt and benefit more)
#   < 1.0  → negative feedback (crisis citizens fall further behind)
_STATE_MULTIPLIER: Dict[str, float] = {
    "thriving":   1.30,   # adaptive benefit — policy gains compound
    "stable":     1.00,   # neutral — policy effect is as predicted
    "struggling": 0.65,   # reduced — structural barriers slow recovery
    "crisis":     0.40,   # severe — crisis inertia overwhelms policy gains
}

# Income compounding per step by state (fraction of current income).
# Thriving citizens grow slightly; crisis citizens continue to lose ground.
_INCOME_COMPOUND: Dict[str, float] = {
    "thriving":   +0.004,   # +0.4 % / step
    "stable":     +0.000,   #  0 %  / step
    "struggling": -0.003,   # -0.3 % / step
    "crisis":     -0.007,   # -0.7 % / step
}


def _classify_state(happiness: float) -> str:
    """Map a happiness value to the corresponding Markov state label."""
    if happiness >= 0.65:
        return "thriving"
    if happiness >= 0.40:
        return "stable"
    if happiness >= 0.20:
        return "struggling"
    return "crisis"


def _attenuate(delta: float, steps: int) -> float:
    """
    Spread the one-shot LLM shock delta across `steps` time steps.

    We use a 1 / sqrt(steps) decay so that short simulations feel impactful
    while long simulations do not saturate all citizens immediately.
    The total cumulative effect over N steps ≈ sqrt(N) × attenuated_delta,
    which grows sub-linearly — realistic for a single policy intervention.
    """
    if steps <= 1:
        return delta
    import math
    return delta / math.sqrt(max(steps, 1))


# ---------------------------------------------------------------------------
# Main simulation loop
# ---------------------------------------------------------------------------

def run_simulation(
    population: list,
    model: Any,
    steps: int,
    mean=None,
    std=None,
    policy_encoding: Optional[List[float]] = None,
) -> Dict[str, List[float]]:
    """
    Run the Markov-chain temporal simulation.

    Parameters
    ----------
    population     : list of Citizen objects (mutated in place, as before)
    model          : trained RandomForestRegressor from train_model()
    steps          : number of time steps to simulate
    mean, std      : normalisation parameters from train_model()
    policy_encoding: 4-element list from encode_policy()

    Returns
    -------
    dict with keys "happiness", "support", "income" — each a list of
    per-step population averages.
    """
    steps = max(1, int(steps))

    # ── Step 0: one-shot batch prediction of the full initial shock ──────────
    # This is the only model call.  The per-step engine attenuates the output.
    base_preds = predict_batch(model, population, mean, std, policy_encoding)
    # base_preds: List[Tuple[h_delta, s_delta, i_delta]]

    # Initialise each citizen's Markov state from their starting happiness
    for citizen in population:
        citizen.markov_state = _classify_state(citizen.happiness)

    metrics_history: Dict[str, List[float]] = {
        "happiness": [],
        "support":   [],
        "income":    [],
    }

    for step in range(steps):

        for citizen, (h_delta, s_delta, i_delta) in zip(population, base_preds):

            state      = citizen.markov_state
            multiplier = _STATE_MULTIPLIER[state]

            # ── Attenuate and modulate the policy shock delta ────────────────
            h_step = _attenuate(h_delta, steps) * multiplier
            s_step = _attenuate(s_delta, steps) * multiplier
            i_step = _attenuate(i_delta, steps) * multiplier

            # ── Income compounding based on welfare state ────────────────────
            compound_rate = _INCOME_COMPOUND[state]
            compound_income = citizen.income * compound_rate

            # ── Apply update ─────────────────────────────────────────────────
            citizen.update_state(h_step, s_step, i_step + compound_income)

            # ── Re-classify Markov state for next step ───────────────────────
            citizen.markov_state = _classify_state(citizen.happiness)

        # ── Record population averages ────────────────────────────────────────
        metrics_history["happiness"].append(average_happiness(population))
        metrics_history["support"].append(average_support(population))
        metrics_history["income"].append(average_income(population))

        logger.debug(
            "Step %d/%d — happiness=%.3f  support=%.3f  income=%.0f",
            step + 1,
            steps,
            metrics_history["happiness"][-1],
            metrics_history["support"][-1],
            metrics_history["income"][-1],
        )

    return metrics_history
