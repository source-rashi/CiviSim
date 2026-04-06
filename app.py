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
from ai_models.llm_interface import simulate_population_reactions
from ai_models.training_model import (
    create_training_data,
    train_model,
    encode_policy
)
from simulation.simulation_engine import run_simulation

st.set_page_config(page_title="CIVISIM", layout="wide")

st.title("CIVISIM — Policy Simulation Dashboard")
st.markdown("Analyze how policies impact a synthetic society.")
st.divider()

top_col1, top_col2 = st.columns([2, 1])

with top_col1:
    policy = st.text_area(
        "Enter Policy",
        height=120,
        placeholder="Example: Increase scholarships for rural OBC students and waive tuition fees for families below ₹3 lakh annual income"
    )

with top_col2:
    steps       = st.slider("Simulation Steps", 5, 50, 10)
    sample_size = st.slider("LLM Sample Size", 50, 200, 200, step=50,
                            help="Citizens sent to Groq. 200 = 20 API calls.")
    run_btn = st.button("Run Simulation", use_container_width=True)

if run_btn:

    if not policy.strip():
        st.error("Please enter a policy description.")
    else:
        st.info(
            f"Pipeline: parse policy → generate 10,000 citizens → "
            f"Groq reacts to {sample_size} in batches of 10 → train model → simulate."
        )

        with st.spinner("Running full simulation..."):

            # ----------------------------------------------------------------
            # Step 1 — Parse policy
            # ----------------------------------------------------------------
            parsed_policy = parse_policy(policy)
            attributes    = map_policy_to_attributes(parsed_policy)

            # ----------------------------------------------------------------
            # Step 2 — Generate population
            # ----------------------------------------------------------------
            population = generate_population(10000, attributes)

            # ----------------------------------------------------------------
            # Step 3 — Batch LLM reactions (Groq, 10 citizens per call)
            # ----------------------------------------------------------------
            reactions, sample_population = simulate_population_reactions(
                population, policy, sample_size=sample_size
            )

            # ----------------------------------------------------------------
            # Step 4 — Train neural model on LLM reactions
            # ----------------------------------------------------------------
            X, y          = create_training_data(sample_population, reactions, parsed_policy)
            model, mean, std = train_model(X, y, epochs=100)

            # ----------------------------------------------------------------
            # Step 5 — Run time simulation
            # Simulation engine owns all state updates.
            # ----------------------------------------------------------------
            policy_encoding = encode_policy(parsed_policy)[0]
            metrics = run_simulation(
                population, model, steps, mean, std, policy_encoding
            )

        st.success("Simulation complete.")
        st.caption(
            f"Processed {len(population):,} citizens across {steps} time steps. "
            f"LLM sample: {len(reactions)} citizens via {len(reactions) // 10} Groq API calls."
        )

        # --------------------------------------------------------------------
        # Policy Context
        # --------------------------------------------------------------------
        st.markdown("### Situation Room")
        st.subheader("Policy Context")
        ctx_col1, ctx_col2, ctx_col3 = st.columns(3)
        with ctx_col1:
            st.write("**Domain:**", parsed_policy["domain"].upper())
        with ctx_col2:
            st.write("**Mechanism:**", parsed_policy.get("mechanism", "N/A").upper())
        with ctx_col3:
            st.write("**Parsed by:**", parsed_policy.get("parsed_by", "keyword").upper())

        if parsed_policy.get("affected_groups"):
            st.write("**Affected Groups:**", ", ".join(parsed_policy["affected_groups"]))

        if parsed_policy.get("potential_winners"):
            win_col, lose_col = st.columns(2)
            with win_col:
                st.success("Winners: " + ", ".join(parsed_policy["potential_winners"]))
            with lose_col:
                if parsed_policy.get("potential_losers"):
                    st.warning("Losers: " + ", ".join(parsed_policy["potential_losers"]))

        st.write("**Relevant Attributes:**", ", ".join(attributes) if attributes else "None")

        # --------------------------------------------------------------------
        # Executive Summary
        # --------------------------------------------------------------------
        st.divider()
        st.markdown("### Executive Summary")

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Avg Happiness",  round(metrics["happiness"][-1], 3))
        kpi2.metric("Policy Support", round(metrics["support"][-1], 3))
        kpi3.metric("Avg Income",     f"₹{int(metrics['income'][-1]):,}")
        kpi4.metric("Population",     f"{len(population):,}")

        # --------------------------------------------------------------------
        # Population Analytics
        # --------------------------------------------------------------------
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
            fig = px.histogram(
                income_list(population),
                nbins=30,
                labels={"value": "Income (₹)", "count": "Citizens"}
            )
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
            sorted_happiness = dict(
                sorted(group_happiness.items(), key=lambda item: item[1], reverse=True)
            )
            fig = px.bar(
                x=list(sorted_happiness.keys()),
                y=list(sorted_happiness.values()),
                labels={"x": "Occupation", "y": "Avg Happiness"}
            )
            st.plotly_chart(fig, use_container_width=True)

        # --------------------------------------------------------------------
        # Policy Trajectory
        # --------------------------------------------------------------------
        st.divider()
        st.markdown("### Policy Trajectory")
        st.subheader(f"Time-Series Trends ({steps} Steps)")

        trend_col1, trend_col2, trend_col3 = st.columns(3)

        with trend_col1:
            fig = px.line(
                y=metrics["happiness"],
                labels={"index": "Step", "y": "Happiness"},
                title="Happiness Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

        with trend_col2:
            fig = px.line(
                y=metrics["support"],
                labels={"index": "Step", "y": "Policy Support"},
                title="Policy Support Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

        with trend_col3:
            fig = px.line(
                y=metrics["income"],
                labels={"index": "Step", "y": "Income (₹)"},
                title="Income Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

        # --------------------------------------------------------------------
        # Individual Citizen Explorer
        # --------------------------------------------------------------------
        st.divider()
        st.markdown("### Individual Lens")
        st.subheader("Citizen Explorer")

        selected_id = st.slider("Select Citizen ID", 0, len(population) - 1, 0)
        citizen = population[selected_id]

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Citizen ID", citizen.cid)
            st.write("**Age:**",        citizen.age)
            st.write("**Income:**",     f"₹{int(citizen.income):,}")
            st.write("**Occupation:**", citizen.occupation)
            st.write("**Caste:**",      citizen.caste)
            st.write("**Location:**",   citizen.location)
        with c2:
            st.write("**Happiness:**",      round(citizen.happiness, 3))
            st.write("**Policy Support:**", round(citizen.policy_support, 3))

        with st.expander("View Traits and Extra Attributes"):
            st.write("**Traits:**",           citizen.traits)
            st.write("**Extra Attributes:**", citizen.extra_attributes)

        # --------------------------------------------------------------------
        # Human Narratives
        # --------------------------------------------------------------------
        st.divider()
        st.markdown("### Human Narratives")
        st.subheader("Citizen Diaries")
        st.caption(f"Showing 5 of {len(reactions)} LLM-simulated reactions.")

        for i, reaction in enumerate(reactions[:5]):
            with st.container(border=True):
                c = sample_population[i]
                st.markdown(
                    f"**Citizen {i + 1}** — {c.age}yr {c.occupation}, "
                    f"{c.caste}, {c.location}, ₹{int(c.income):,}/month"
                )
                st.write(reaction.get("diary_entry", "No entry available."))
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Happiness Δ", round(reaction.get("happiness_change", 0), 3))
                col_b.metric("Support Δ",   round(reaction.get("support_change", 0), 3))
                col_c.metric("Income Δ",    f"₹{int(reaction.get('income_change', 0)):,}")