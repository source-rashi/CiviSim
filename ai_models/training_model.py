import copy
import logging
import random
from typing import Optional

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature normalization
# ---------------------------------------------------------------------------

def normalize_features(X):
    """
    Normalize feature matrix using mean/std.
    Returns normalized X, plus the mean and std used —
    these MUST be saved and reused for evaluation and inference.
    Never recompute mean/std from eval data.
    """
    X = np.array(X, dtype=np.float32)
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8  # avoid division by zero
    X_norm = (X - mean) / std
    return X_norm, mean, std


def apply_normalization(X, mean, std):
    """
    Apply pre-computed normalization to new data.
    Always use the mean/std from training — never recompute.
    """
    X = np.array(X, dtype=np.float32)
    return (X - mean) / (std + 1e-8)


# ---------------------------------------------------------------------------
# Policy encoding
# ---------------------------------------------------------------------------

DOMAIN_MAP = {
    "education":   0,
    "tax":         1,
    "agriculture": 2,
    "health":      3,
    "general":     4,
}

MECHANISM_MAP = {
    "subsidy": 0,
    "tax_change": 1,
    "regulation": 2,
    "restriction": 3,
    "investment": 4,
    "reform": 5,
    "general": 6,
}

TIME_EFFECT_MAP = {
    "immediate": 0,
    "gradual": 1,
    "long_term": 2,
}

MAX_AFFECTED_GROUPS = 8.0


def _normalize_lookup(mapping, key, fallback="general"):
    max_index = max(mapping.values()) if mapping else 1
    mapped = mapping.get(str(key).strip().lower(), mapping.get(fallback, max_index))
    return float(mapped) / float(max(max_index, 1))


def encode_policy(policy):
    """
    Return normalized policy features for model conditioning.

    Feature order:
      1) domain score
      2) mechanism score
      3) time-effect score
      4) affected-group intensity
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


def set_random_seed(seed: int) -> None:
    """Set deterministic seeds across Python, NumPy, and PyTorch."""
    random.seed(seed)
    np.random.seed(seed % (2**32 - 1))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
# Training data assembly
# ---------------------------------------------------------------------------

def create_training_data(population, llm_results, policy=None):
    """
    Build (X, y) arrays from citizen profiles and LLM reactions.

    Features (9D):
        age, income, risk_tolerance, openness, political_leaning,
        policy_domain, policy_mechanism, policy_time_effect, affected_group_intensity

    Targets (3D):
        happiness_change, support_change, income_change
    """
    X = []
    y = []

    policy_features = encode_policy(policy)

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
# Model architecture
# ---------------------------------------------------------------------------

class ReactionModel(nn.Module):
    """
    Lightweight feedforward network:
        9 inputs -> 16 -> 8 -> 3 outputs

    Outputs:
        [0] happiness_delta  — interpreted as [-1, 1] score
        [1] support_delta    — interpreted as [-1, 1] score
        [2] income_delta     — interpreted as raw rupee change (scaled in predictor)
    """

    def __init__(self, input_size=9):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_size, 16),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(16, 8),
            nn.BatchNorm1d(8),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(8, 3),
        )

    def forward(self, x):
        return self.network(x)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def _build_stratification_keys(y_array):
    """
    Build stratification keys from support and income targets to reduce
    high-variance train/validation splits on small datasets.
    """
    support_bucket = np.digitize(y_array[:, 1], [-0.25, 0.0, 0.25]).astype(np.int64)
    income_bucket = np.digitize(y_array[:, 2], [-2500.0, 0.0, 2500.0]).astype(np.int64)
    return support_bucket * 10 + income_bucket


def _split_train_val_indices(strat_keys, val_count, rng):
    sample_count = len(strat_keys)
    if sample_count <= 1 or val_count <= 0:
        return np.array([], dtype=np.int64), np.arange(sample_count, dtype=np.int64)

    desired_val = min(max(int(val_count), 0), sample_count - 1)
    groups = {}
    for idx, key in enumerate(strat_keys):
        groups.setdefault(int(key), []).append(idx)

    val_idx = []
    for group_indices in groups.values():
        group_array = np.array(group_indices, dtype=np.int64)
        rng.shuffle(group_array)
        proportional = int(round(len(group_array) * desired_val / sample_count))

        if len(group_array) > 1:
            group_val_count = max(1, min(proportional, len(group_array) - 1))
        else:
            group_val_count = 0

        val_idx.extend(group_array[:group_val_count].tolist())

    if len(val_idx) > desired_val:
        rng.shuffle(val_idx)
        val_idx = val_idx[:desired_val]

    val_idx_set = set(val_idx)
    if len(val_idx) < desired_val:
        remaining = [idx for idx in range(sample_count) if idx not in val_idx_set]
        rng.shuffle(remaining)
        val_idx.extend(remaining[: desired_val - len(val_idx)])
        val_idx_set = set(val_idx)

    train_idx = [idx for idx in range(sample_count) if idx not in val_idx_set]
    if not train_idx and val_idx:
        moved = val_idx.pop()
        train_idx = [moved]

    return np.array(val_idx, dtype=np.int64), np.array(train_idx, dtype=np.int64)

def train_model(
    X,
    y,
    epochs=200,
    validation_split=0.2,
    return_metrics=False,
    batch_size=32,
    seed: Optional[int] = None,
    early_stopping_patience=12,
    min_delta=1e-4,
):
    """
    Train ReactionModel on (X, y) with deterministic, mini-batch optimization.

    Returns: (model, train_mean, train_std) by default.
    If return_metrics=True, returns (model, train_mean, train_std, diagnostics).
    The mean and std MUST be passed to evaluate_model and predict_batch.
    """
    if seed is not None:
        set_random_seed(int(seed))

    X_norm, mean, std = normalize_features(X)

    X_array = np.array(X_norm, dtype=np.float32)
    y_array = np.array(y, dtype=np.float32)

    sample_count = len(X_array)
    if sample_count == 0:
        raise ValueError("Cannot train model with empty training data.")

    rng = np.random.default_rng(seed)
    requested_val = max(0.0, min(0.5, float(validation_split)))
    val_count = max(1, int(sample_count * requested_val)) if sample_count >= 10 else 0
    if val_count >= sample_count:
        val_count = max(0, sample_count - 1)

    if val_count > 0:
        strat_keys = _build_stratification_keys(y_array)
        val_idx, train_idx = _split_train_val_indices(strat_keys, val_count, rng)
    else:
        val_idx = np.array([], dtype=np.int64)
        train_idx = np.arange(sample_count, dtype=np.int64)

    if len(train_idx) == 0:
        raise ValueError("Cannot train model because training split is empty.")

    X_train = torch.tensor(X_array[train_idx], dtype=torch.float32)
    y_train = torch.tensor(y_array[train_idx], dtype=torch.float32)

    X_val = torch.tensor(X_array[val_idx], dtype=torch.float32) if val_count > 0 else None
    y_val = torch.tensor(y_array[val_idx], dtype=torch.float32) if val_count > 0 else None

    model = ReactionModel(input_size=X_array.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.6,
        patience=4,
        min_lr=1e-5,
    )
    loss_fn = nn.MSELoss()

    effective_batch_size = max(1, min(int(batch_size), len(train_idx)))
    num_batches = (len(train_idx) + effective_batch_size - 1) // effective_batch_size

    best_metric = float("inf")
    best_epoch = 0
    best_state = copy.deepcopy(model.state_dict())
    epochs_without_improvement = 0
    epochs_completed = 0
    patience = max(0, int(early_stopping_patience))
    min_delta = float(min_delta)

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0

        perm = torch.randperm(X_train.size(0))
        X_train_shuffled = X_train[perm]
        y_train_shuffled = y_train[perm]

        for batch_idx in range(num_batches):
            start_idx = batch_idx * effective_batch_size
            end_idx = min(start_idx + effective_batch_size, X_train.size(0))
            X_batch = X_train_shuffled[start_idx:end_idx]
            y_batch = y_train_shuffled[start_idx:end_idx]

            predictions = model(X_batch)
            loss = loss_fn(predictions, y_batch)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()

        avg_epoch_loss = epoch_loss / max(num_batches, 1)

        model.eval()
        with torch.no_grad():
            if X_val is not None and y_val is not None:
                val_preds = model(X_val)
                tracked_metric = loss_fn(val_preds, y_val).item()
            else:
                tracked_metric = avg_epoch_loss

        scheduler.step(tracked_metric)
        epochs_completed = epoch + 1

        if tracked_metric + min_delta < best_metric:
            best_metric = tracked_metric
            best_epoch = epoch + 1
            best_state = copy.deepcopy(model.state_dict())
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        if epoch % 20 == 0:
            logger.debug(
                "Epoch %3d - train_loss: %.6f tracked_metric: %.6f",
                epoch,
                avg_epoch_loss,
                tracked_metric,
            )

        if X_val is not None and y_val is not None and patience > 0:
            if epochs_without_improvement >= patience:
                logger.info(
                    "Early stopping at epoch %s (best_epoch=%s, best_val=%.6f).",
                    epoch + 1,
                    best_epoch,
                    best_metric,
                )
                break

    model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        train_preds = model(X_train)
        train_loss = loss_fn(train_preds, y_train).item()
        train_mae = torch.mean(torch.abs(train_preds - y_train)).item()

        if X_val is not None and y_val is not None:
            val_preds = model(X_val)
            val_loss = loss_fn(val_preds, y_val).item()
            val_mae = torch.mean(torch.abs(val_preds - y_val)).item()
        else:
            val_loss = None
            val_mae = None

    diagnostics = {
        "samples_total": int(sample_count),
        "samples_train": int(len(train_idx)),
        "samples_validation": int(len(val_idx)),
        "train_loss": float(train_loss),
        "train_mae": float(train_mae),
        "validation_loss": float(val_loss) if val_loss is not None else None,
        "validation_mae": float(val_mae) if val_mae is not None else None,
        "epochs_requested": int(epochs),
        "epochs_completed": int(epochs_completed),
        "early_stopped": bool(X_val is not None and y_val is not None and epochs_completed < int(epochs)),
        "best_epoch": int(best_epoch),
        "best_validation_loss": float(best_metric) if val_loss is not None else None,
        "effective_batch_size": int(effective_batch_size),
        "random_seed": int(seed) if seed is not None else None,
        "train_validation_mae_gap": (
            float(abs(train_mae - val_mae))
            if val_mae is not None
            else None
        ),
    }

    logger.info(
        "Training complete. train_loss=%.6f val_loss=%s",
        train_loss,
        f"{val_loss:.6f}" if val_loss is not None else "n/a",
    )

    if return_metrics:
        return model, mean, std, diagnostics

    return model, mean, std


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_model(model, X, y, train_mean, train_std):
    """
    Evaluate model on held-out data.

    IMPORTANT: always pass the mean and std from training (returned by train_model).
    Never recompute normalization from the eval set — the scale must match training.
    """
    # BUG FIX: was recomputing std from eval data instead of using train_std
    X_norm = apply_normalization(X, train_mean, train_std)

    model.eval()
    X_tensor = torch.tensor(X_norm, dtype=torch.float32)
    y_tensor = torch.tensor(np.array(y, dtype=np.float32), dtype=torch.float32)

    with torch.no_grad():
        predictions = model(X_tensor)

    loss = ((predictions - y_tensor) ** 2).mean()
    logger.info(f"Evaluation loss: {loss.item():.6f}")
    return loss.item()