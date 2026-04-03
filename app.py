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
from ai_models.llm_interface import simulate_citizen_reaction
from ai_models.training_model import (
    create_training_data,
    train_model,
    encode_policy
)
from simulation.simulation_engine import run_simulation

st.set_page_config(
    page_title="CIVISIM",
    layout="wide"
)

# ================================================================
# GLOBAL THEME & STYLING (Phase F1: Design System)
# ================================================================
st.markdown("""
<style>

/* Global dark theme */
body {
    background-color: #0A0F1C;
    color: #E0E7FF;
}

.block-container {
    padding-top: 2rem;
}

/* Card styling for consistent layout */
.card {
    background-color: #1C2536;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 20px;
    border-left: 4px solid #6366F1;
}

.metric-card {
    background-color: #1C2536;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}

/* Typography */
h1, h2, h3 {
    color: #E0E7FF;
}

/* Dividers */
hr {
    border-color: #2D3748;
}

</style>
""", unsafe_allow_html=True)

st.title("CIVISIM — Policy Simulation Dashboard")
st.markdown("Analyze how policies impact a synthetic society.")
st.divider()

# ================================================================
# NAVIGATION BAR (Phase F1: Base Layout)
# ================================================================
navbar_col1, navbar_col2, navbar_col3 = st.columns([1, 4, 2])

with navbar_col1:
    st.markdown("### 🎲 CIVISIM")

with navbar_col2:
    st.markdown(
        """
        **Simulator** | Dashboard | Gallery | How it Works | About
        """
    )

with navbar_col3:
    st.markdown(
        """
        [GitHub](https://github.com/source-rashi/CiviSim) | [Docs](/)
        """
    )

st.divider()

# ================================================================
# INPUT SECTION: Policy Configuration
# ================================================================
input_col1, input_col2 = st.columns([2, 1])

with input_col1:
    policy = st.text_area(
        "Enter Policy",
        height=120,
        placeholder="Example: Increase scholarships for rural OBC students and reduce tuition fees"
    )

with input_col2:
    steps = st.slider("Simulation Steps", 5, 50, 10)
    run_btn = st.button("Run Simulation", use_container_width=True)

if run_btn:

    if not policy.strip():
        st.error("Please enter a policy description.")
    else:
        st.info("Launching pipeline: parse policy → generate population → collect reactions → train model → simulate.")

        with st.spinner("Running full simulation..."):

            # ----------------------------------------------------------------
            # Step 1 — Parse policy and map to citizen attributes
            # ----------------------------------------------------------------
            parsed_policy = parse_policy(policy)
            attributes = map_policy_to_attributes(parsed_policy)

            # ----------------------------------------------------------------
            # Step 2 — Generate synthetic population
            # ----------------------------------------------------------------
            population = generate_population(10000, attributes)

            # ----------------------------------------------------------------
            # Step 3 — Sample citizens and collect LLM reactions
            # ----------------------------------------------------------------
            sample_size = min(50, len(population))
            sample_population = population[:sample_size]
            reactions = []

            for citizen in sample_population:
                # simulate_citizen_reaction now returns a parsed dict directly
                reaction = simulate_citizen_reaction(citizen, policy)
                reactions.append(reaction)

            # ----------------------------------------------------------------
            # Step 4 — Train neural model on LLM reactions
            # ----------------------------------------------------------------
            X, y = create_training_data(sample_population, reactions, parsed_policy)
            model, mean, std = train_model(X, y, epochs=100)

            # ----------------------------------------------------------------
            # Step 5 — Run time simulation
            # The simulation engine owns ALL state updates.
            # Do NOT call predict_batch or update_state here —
            # run_simulation handles both internally.
            # ----------------------------------------------------------------
            policy_encoding = encode_policy(parsed_policy)[0]
            metrics = run_simulation(
                population, model, steps, mean, std, policy_encoding
            )

        st.success("Simulation complete.")
        st.caption(f"Processed {len(population):,} citizens across {steps} time steps.")

        # --------------------------------------------------------------------
        # Dashboard — Policy Context
        # --------------------------------------------------------------------
        st.markdown("### Situation Room")
        st.subheader("Policy Context")
        ctx_col1, ctx_col2 = st.columns(2)
        with ctx_col1:
            st.write("**Domain:**", parsed_policy["domain"].upper())
        with ctx_col2:
            st.write("**Relevant Attributes:**", ", ".join(attributes) if attributes else "None detected")

        # --------------------------------------------------------------------
        # Dashboard — Executive Summary
        # --------------------------------------------------------------------
        st.divider()
        st.markdown("### Executive Summary")

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Avg Happiness",  round(metrics["happiness"][-1], 3))
        kpi2.metric("Policy Support", round(metrics["support"][-1], 3))
        kpi3.metric("Avg Income",     f"₹{int(metrics['income'][-1]):,}")
        kpi4.metric("Population",     f"{len(population):,}")

        # --------------------------------------------------------------------
        # Dashboard — Population Analytics
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
        # Dashboard — Policy Trajectory
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
        # Dashboard — Individual Citizen Explorer
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
            st.write("**Traits:**",            citizen.traits)
            st.write("**Extra Attributes:**",  citizen.extra_attributes)

        # --------------------------------------------------------------------
        # Dashboard — Human Narratives
        # --------------------------------------------------------------------
        st.divider()
        st.markdown("### Human Narratives")
        st.subheader("Citizen Diaries")
        st.caption("First-person accounts from the sampled citizens.")

        for i, reaction in enumerate(reactions[:5]):
            with st.container(border=True):
                st.markdown(f"**Citizen {i + 1}**")
                st.write(reaction.get("diary_entry", "No diary entry available."))
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Happiness Δ", round(reaction.get("happiness_change", 0), 3))
                col_b.metric("Support Δ",   round(reaction.get("support_change", 0), 3))
                col_c.metric("Income Δ",    f"₹{int(reaction.get('income_change', 0)):,}")