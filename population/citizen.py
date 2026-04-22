"""
citizen.py — Synthetic citizen data model.

The `markov_state` field is used by the Markov-chain simulation engine
(simulation_engine.py) to track each citizen's welfare tier across time
steps.  It has no effect on the LLM sampling or NN training phases.

States: "thriving" | "stable" | "struggling" | "crisis"
"""


class Citizen:

    def __init__(
        self,
        cid,
        age,
        gender,
        income,
        occupation,
        caste,
        education,
        location,
        traits,
        extra_attributes=None,
    ):
        self.cid = cid
        self.age = age
        self.gender = gender
        self.income = income
        self.occupation = occupation
        self.caste = caste
        self.education = education
        self.location = location
        self.traits = traits
        self.extra_attributes = extra_attributes or {}

        # Simulation states
        self.happiness = 0.5
        self.policy_support = 0.5

        # Markov welfare state — initialised from starting happiness
        # (all citizens start at 0.5, so "stable" is always correct)
        self.markov_state: str = "stable"

    def update_state(
        self,
        happiness_delta: float,
        support_delta: float,
        income_delta: float,
    ) -> None:
        """
        Apply per-step deltas and clamp to realistic bounds.
        The simulation engine calls this after deriving state-modulated deltas.
        """
        self.happiness += happiness_delta
        self.policy_support += support_delta
        self.income += income_delta

        # Clamp to realistic bounds
        self.happiness = max(0.0, min(1.0, self.happiness))
        self.policy_support = max(0.0, min(1.0, self.policy_support))
        self.income = max(0.0, self.income)

    def to_dict(self) -> dict:
        return {
            "id":           self.cid,
            "age":          self.age,
            "income":       self.income,
            "occupation":   self.occupation,
            "caste":        self.caste,
            "markov_state": self.markov_state,
        }
