def map_policy_to_attributes(policy):

    domain = policy["domain"]

    if domain == "education":

        return [
            "caste",
            "education",
            "income",
            "student_status"
        ]

    elif domain == "agriculture":

        return [
            "land_size",
            "crop_type",
            "loan",
            "rural"
        ]

    elif domain == "tax":

        return [
            "income",
            "occupation",
            "tax_bracket"
        ]

    else:

        return [
            "income",
            "occupation"
        ]
