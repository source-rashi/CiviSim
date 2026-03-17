from collections import Counter


def occupation_distribution(population):

    occupations = [c.occupation for c in population]
    return dict(Counter(occupations))


def caste_distribution(population):

    castes = [c.caste for c in population]
    return dict(Counter(castes))


def income_list(population):

    return [c.income for c in population]


def average_income(population):

    incomes = income_list(population)
    return sum(incomes) / len(incomes)


def average_happiness(population):

    return sum(c.happiness for c in population) / len(population)


def average_support(population):

    return sum(c.policy_support for c in population) / len(population)
