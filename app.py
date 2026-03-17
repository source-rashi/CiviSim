import streamlit as st
import plotly.express as px
from population.population_generator import generate_population
from utils.metrics import (
    occupation_distribution,
    caste_distribution,
    income_list
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
from ai_models.reaction_predictor import predict_reaction
from simulation.simulation_engine import run_simulation

st.set_page_config(
    page_title="CIVISIM",
    layout="wide"
)

st.title("CIVISIM — Synthetic Policy Simulator")

st.markdown(
    "Test public policies on a virtual society."
)

policy = st.text_area(
    "Enter Policy Description",
    height=150
)

steps = st.slider("Simulation Steps", 5, 50, 10)

if st.button("Run Simulation"):

    if not policy.strip():
        st.error("Please enter a policy description")
    else:
        parsed_policy = parse_policy(policy)

        attributes = map_policy_to_attributes(parsed_policy)

        st.subheader("Policy Analysis")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Domain:**", parsed_policy["domain"].upper())
        with col2:
            st.write("**Relevant Attributes:**", ", ".join(attributes))

        population = generate_population(10000, attributes)

        occ_dist = occupation_distribution(population)
        caste_dist = caste_distribution(population)
        incomes = income_list(population)

        st.success("Population Generated Successfully")

        col1, col2 = st.columns(2)

        with col1:

            st.subheader("Occupation Distribution")

            fig = px.bar(
                x=list(occ_dist.keys()),
                y=list(occ_dist.values())
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:

            st.subheader("Caste Distribution")

            fig = px.pie(
                names=list(caste_dist.keys()),
                values=list(caste_dist.values())
            )

            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Income Distribution")

        fig = px.histogram(incomes, nbins=30)

        st.plotly_chart(fig, use_container_width=True)

        # Simulate LLM reactions for sample population
        st.divider()
        st.subheader("Citizen Reaction Simulation (Sample)")

        # Performance control: limit sample size to avoid excessive API calls
        sample_size = min(50, len(population))
        sample_population = population[:sample_size]
        reactions = []

        st.warning(f"⚠️ Simulating reactions for {sample_size} citizens. This will use Gemini API calls.")

        with st.spinner("Simulating citizen reactions..."):
            for i, citizen in enumerate(sample_population):
                raw_response = simulate_citizen_reaction(citizen, policy)
                parsed_reaction = parse_llm_output(raw_response)
                parsed_reaction["citizen_id"] = i
                reactions.append(parsed_reaction)

        st.success(f"✓ Simulated reactions for {len(reactions)} citizens using Gemini LLM")

        # Display diary entries
        st.subheader("Citizen Reactions (Sample)")

        for i, reaction in enumerate(reactions[:5]):
            with st.container(border=True):
                st.markdown(f"**Citizen {reaction['citizen_id'] + 1} Diary:**")
                st.write(reaction.get("diary_entry", "No response generated"))

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Happiness Change", f"{reaction.get('happiness_change', 0):.2f}")
                with col2:
                    st.metric("Support Change", f"{reaction.get('support_change', 0):.2f}")
                with col3:
                    st.metric("Income Change", f"₹{reaction.get('income_change', 0):.0f}")

        # Train neural network on LLM data
        st.divider()
        st.subheader("Training Neural Network for Full Population")

        with st.spinner("Training neural network on LLM data..."):
            X, y = create_training_data(sample_population, reactions, parsed_policy)
            model, mean, std = train_model(X, y, epochs=100)

        st.success(f"✓ Neural network trained on {len(reactions)} citizen samples")

        # Apply neural network to entire population
        st.subheader("Full Population Reaction Simulation (Using Neural Network)")

        # Get policy encoding for predictions
        policy_encoding = encode_policy(parsed_policy)[0]

        with st.spinner("Predicting reactions for all 10,000 citizens..."):
            happiness_changes = []
            support_changes = []
            income_changes = []

            for citizen in population:
                pred = predict_reaction(model, citizen, mean, std, policy_encoding)
                
                happiness_delta = float(pred[0])
                support_delta = float(pred[1])
                income_delta = float(pred[2])
                
                citizen.update_state(
                    happiness_delta,
                    support_delta,
                    income_delta
                )
                
                happiness_changes.append(citizen.happiness)
                support_changes.append(citizen.policy_support)
                income_changes.append(citizen.income)

        st.success(f"✓ Predicted reactions for {len(population)} citizens using neural network model")

        # Display impact metrics
        st.subheader("Population Impact Metrics")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_happiness = sum(happiness_changes) / len(happiness_changes)
            st.metric("Average Happiness", f"{avg_happiness:.2f}")
        with col2:
            avg_support = sum(support_changes) / len(support_changes)
            st.metric("Average Support", f"{avg_support:.2f}")
        with col3:
            avg_income = sum(income_changes) / len(income_changes)
            st.metric("Average Income", f"₹{avg_income:.0f}")
        with col4:
            st.metric("Population Size", len(population))

        # Display distribution of impact
        st.subheader("Distribution of Citizen Reactions")

        col1, col2 = st.columns(2)

        with col1:
            fig = px.histogram(happiness_changes, nbins=30, title="Happiness Distribution")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.histogram(support_changes, nbins=30, title="Policy Support Distribution")
            st.plotly_chart(fig, use_container_width=True)

        # Time-step simulation
        st.divider()
        st.subheader(f"Time-Step Simulation ({steps} steps)")

        with st.spinner(f"Running {steps}-step simulation..."):
            metrics = run_simulation(
                population, model, steps, mean, std, policy_encoding
            )

        st.success(f"Simulation complete: {steps} steps across {len(population):,} citizens")

        col1, col2, col3 = st.columns(3)

        with col1:
            fig = px.line(
                y=metrics["happiness"],
                labels={"x": "Step", "y": "Happiness"},
                title="Happiness Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.line(
                y=metrics["support"],
                labels={"x": "Step", "y": "Policy Support"},
                title="Policy Support Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col3:
            fig = px.line(
                y=metrics["income"],
                labels={"x": "Step", "y": "Income"},
                title="Income Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)
