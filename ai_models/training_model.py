import torch
import torch.nn as nn
import numpy as np
import logging

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


def encode_policy(policy):
    """Return a single-element list with the integer domain code."""
    domain = policy.get("domain", "general") if policy else "general"
    return [DOMAIN_MAP.get(domain, 4)]


# ---------------------------------------------------------------------------
# Training data assembly
# ---------------------------------------------------------------------------

def create_training_data(population, llm_results, policy=None):
    """
    Build (X, y) arrays from citizen profiles and LLM reactions.

    Features (6D):
        age, income, risk_tolerance, openness, political_leaning, policy_domain

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
            policy_features[0],
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
        6 inputs → 64 → 32 → 16 → 3 outputs

    Outputs:
        [0] happiness_delta  — interpreted as [-1, 1] score
        [1] support_delta    — interpreted as [-1, 1] score
        [2] income_delta     — interpreted as raw rupee change (scaled in predictor)
    """

    def __init__(self, input_size=6):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(32, 16),
            nn.ReLU(),

            nn.Linear(16, 3),
        )

    def forward(self, x):
        return self.network(x)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_model(X, y, epochs=200):
    """
    Train ReactionModel on (X, y).
    Returns: (model, train_mean, train_std)
    The mean and std MUST be passed to evaluate_model and predict_batch.
    """
    X_norm, mean, std = normalize_features(X)

    X_tensor = torch.tensor(X_norm, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32)

    model = ReactionModel(input_size=X_norm.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_fn = nn.MSELoss()

    for epoch in range(epochs):
        model.train()
        predictions = model(X_tensor)
        loss = loss_fn(predictions, y_tensor)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if epoch % 40 == 0:
            logger.debug(f"Epoch {epoch:3d} — loss: {loss.item():.6f}")

    logger.info(f"Training complete. Final loss: {loss.item():.6f}")
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