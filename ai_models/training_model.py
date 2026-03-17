import torch
import torch.nn as nn


def create_training_data(population, llm_results):

    X = []
    y = []

    for citizen, result in zip(population, llm_results):

        features = [
            citizen.age,
            citizen.income,
            len(citizen.traits),
            citizen.traits["risk_tolerance"],
            citizen.traits["openness"],
            citizen.traits["political_leaning"]
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

    def __init__(self):

        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(6, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 3)
        )

    def forward(self, x):

        return self.network(x)


def train_model(X, y, epochs=100):

    model = ReactionModel()

    X_tensor = torch.tensor(X, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_fn = nn.MSELoss()

    for epoch in range(epochs):

        predictions = model(X_tensor)

        loss = loss_fn(predictions, y_tensor)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    return model

