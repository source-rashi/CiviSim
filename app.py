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

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Average Happiness")
    st.line_chart([0, 1, 2, 3])

with col2:
    st.subheader("Policy Support")
    st.line_chart([3, 2, 5, 4])
