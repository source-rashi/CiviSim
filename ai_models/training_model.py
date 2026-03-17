import torch
import torch.nn as nn
import numpy as np


def normalize_features(X):

    X = np.array(X)

    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8

    X_norm = (X - mean) / std

    return X_norm, mean, std


def denormalize_features(X_norm, mean, std):

    return X_norm * std + mean


def encode_policy(policy):

    domain_map = {
        "education": 0,
        "tax": 1,
        "agriculture": 2,
        "general": 3
    }

    return [domain_map.get(policy["domain"], 3)]


def create_training_data(population, llm_results, policy=None):

    X = []
    y = []

    policy_features = encode_policy(policy) if policy else [3]

    for citizen, result in zip(population, llm_results):

        features = [
            citizen.age,
            citizen.income,
            citizen.traits["risk_tolerance"],
            citizen.traits["openness"],
            citizen.traits["political_leaning"],
            policy_features[0]
        ]

        targets = [
            result["happiness_change"],
            result["support_change"],
            result["income_change"]
        ]

        X.append(features)
        y.append(targets)

    return X, y


class ReactionModel(nn.Module):

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

            nn.Linear(16, 3)
        )

    def forward(self, x):

        return self.network(x)


def train_model(X, y, epochs=200):

    X_norm, mean, std = normalize_features(X)

    model = ReactionModel(input_size=X_norm.shape[1])

    X_tensor = torch.tensor(X_norm, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32)

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
            print(f"Epoch {epoch:3d}, Loss: {loss.item():.6f}")

    return model, mean, std


def evaluate_model(model, X, y, mean, std):

    X_norm = (np.array(X) - mean) / (np.std(np.array(X), axis=0) + 1e-8)

    model.eval()

    X_tensor = torch.tensor(X_norm, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32)

    with torch.no_grad():
        predictions = model(X_tensor)

    loss = ((predictions - y_tensor) ** 2).mean()

    return loss.item()

