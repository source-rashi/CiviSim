import streamlit as st
import plotly.express as px
from population.population_generator import generate_population
from utils.metrics import (
    occupation_distribution,
    caste_distribution,
    income_list,
    group_by_attribute,
    group_average_happiness
)
from policy_engine.policy_parser import parse_policy
from policy_engine.policy_mapper import map_policy_to_attributes
from ai_models.llm_interface import (
    simulate_citizen_reaction,
    parse_llm_output
)
from ai_models.training_model import (
    create_training_data,
    train_model,
    encode_policy
)
from ai_models.reaction_predictor import predict_batch
from simulation.simulation_engine import run_simulation

st.set_page_config(
    page_title="CIVISIM",
    layout="wide"
)

st.title("CIVISIM — Policy Simulation Dashboard")
st.markdown("Analyze how policies impact a synthetic society.")
st.divider()

top_col1, top_col2 = st.columns([2, 1])

with top_col1:
    policy = st.text_area(
        "Enter Policy",
        height=120,
        placeholder="Example: Increase scholarships for rural students and reduce tuition fees"
    )

with top_col2:
    steps = st.slider("Simulation Steps", 5, 50, 10)
    run_btn = st.button("Run Simulation", use_container_width=True)

if run_btn:

    if not policy.strip():
        st.error("Please enter a policy description")
    else:
        st.info("Launching pipeline: parse policy, generate population, train model, and simulate time steps.")
        with st.spinner("Running full simulation..."):
            parsed_policy = parse_policy(policy)
            attributes = map_policy_to_attributes(parsed_policy)
            population = generate_population(10000, attributes)

            sample_size = min(50, len(population))
            sample_population = population[:sample_size]
            reactions = []

            for i, citizen in enumerate(sample_population):
                parsed_reaction = simulate_citizen_reaction(citizen, policy)
                parsed_reaction["citizen_id"] = i
                reactions.append(parsed_reaction)

            X, y = create_training_data(sample_population, reactions, parsed_policy)
            model, mean, std = train_model(X, y, epochs=100)

            policy_encoding = encode_policy(parsed_policy)[0]
            preds = predict_batch(model, population, mean, std, policy_encoding)

            happiness_changes = []
            support_changes = []
            income_changes = []

            for citizen, pred in zip(population, preds):
                citizen.update_state(
                    float(pred[0]),
                    float(pred[1]),
                    float(pred[2])
                )
                happiness_changes.append(citizen.happiness)
                support_changes.append(citizen.policy_support)
                income_changes.append(citizen.income)

            metrics = run_simulation(
                population, model, steps, mean, std, policy_encoding
            )

        st.success("Simulation Complete")
        st.caption(f"Processed {len(population):,} citizens across {steps} steps.")

        st.markdown("### Situation Room")
        st.subheader("Policy Context")
        ctx_col1, ctx_col2 = st.columns(2)
        with ctx_col1:
            st.write("Domain:", parsed_policy["domain"].upper())
        with ctx_col2:
            st.write("Relevant Attributes:", ", ".join(attributes))

        st.divider()
        st.markdown("### Executive Summary")
        st.subheader("Key Metrics")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Avg Happiness", round(metrics["happiness"][-1], 2))
        kpi2.metric("Policy Support", round(metrics["support"][-1], 2))
        kpi3.metric("Avg Income", int(metrics["income"][-1]))
        kpi4.metric("Population", len(population))

        st.divider()
        st.markdown("### Population Analytics")
        viz_left, viz_right = st.columns(2)

        with viz_left:
            st.subheader("Occupation Distribution")
            occ_dist = occupation_distribution(population)
            fig = px.bar(
                x=list(occ_dist.keys()),
                y=list(occ_dist.values()),
                labels={"x": "Occupation", "y": "Citizens"}
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Income Distribution")
            fig = px.histogram(income_list(population), nbins=30)
            st.plotly_chart(fig, use_container_width=True)

        with viz_right:
            st.subheader("Caste Distribution")
            caste_dist = caste_distribution(population)
            fig = px.pie(
                names=list(caste_dist.keys()),
                values=list(caste_dist.values())
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Happiness by Occupation")
            groups = group_by_attribute(population, "occupation")
            group_happiness = group_average_happiness(groups)
            sorted_group_happiness = dict(
                sorted(group_happiness.items(), key=lambda item: item[1], reverse=True)
            )
            fig = px.bar(
                x=list(sorted_group_happiness.keys()),
                y=list(sorted_group_happiness.values()),
                labels={"x": "Occupation", "y": "Avg Happiness"}
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown("### Policy Trajectory")
        st.subheader(f"Time-Series Trends ({steps} Steps)")
        trend_col1, trend_col2, trend_col3 = st.columns(3)

        with trend_col1:
            fig = px.line(
                y=metrics["happiness"],
                labels={"x": "Step", "y": "Happiness"},
                title="Happiness Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

        with trend_col2:
            fig = px.line(
                y=metrics["support"],
                labels={"x": "Step", "y": "Policy Support"},
                title="Policy Support Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

        with trend_col3:
            fig = px.line(
                y=metrics["income"],
                labels={"x": "Step", "y": "Income"},
                title="Income Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown("### Individual Lens")
        st.subheader("Citizen Explorer")
        selected_id = st.slider("Select Citizen ID", 0, len(population) - 1, 0)
        citizen = population[selected_id]

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Citizen ID", citizen.cid)
            st.write("Age:", citizen.age)
            st.write("Income:", int(citizen.income))
            st.write("Occupation:", citizen.occupation)
            st.write("Caste:", citizen.caste)
        with c2:
            st.write("Happiness:", round(citizen.happiness, 3))
            st.write("Policy Support:", round(citizen.policy_support, 3))

        with st.expander("View Traits and Extra Attributes"):
            st.write("Traits:", citizen.traits)
            st.write("Extra Attributes:", citizen.extra_attributes)

        st.divider()
        st.markdown("### Human Narratives")
        st.subheader("Citizen Diaries")
        for i, res in enumerate(reactions[:5]):
            with st.container(border=True):
                st.markdown(f"**Citizen {i + 1}:**")
                st.write(res.get("diary_entry", "No diary entry available"))
