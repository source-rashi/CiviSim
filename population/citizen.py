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
        traits
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

        # Simulation states
        self.happiness = 0.5
        self.policy_support = 0.5

    def update_state(
        self,
        happiness_delta,
        support_delta,
        income_delta
    ):

        self.happiness += happiness_delta
        self.policy_support += support_delta
        self.income += income_delta

    def to_dict(self):

        return {
            "id": self.cid,
            "age": self.age,
            "income": self.income,
            "occupation": self.occupation,
            "caste": self.caste
        }
