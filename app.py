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
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================================================================
# PHASE F-ULTRA 1: PREMIUM DESIGN SYSTEM
# ================================================================

# Task F1.1: Remove Default Streamlit UI
st.markdown("""
<style>

/* Hide default Streamlit UI elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Global background with gradient */
body {
    background: linear-gradient(135deg, #0A0F1C, #0F172A);
    color: #E0E7FF;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Optimize container padding */
.block-container {
    padding-top: 1rem;
    padding-left: 3rem;
    padding-right: 3rem;
    max-width: 1400px;
    margin: 0 auto;
}

/* Typography excellence */
h1, h2, h3, h4 {
    font-weight: 600;
    letter-spacing: -0.5px;
    color: #E0E7FF;
}

h1 {
    font-size: 2.5rem;
    line-height: 1.2;
}

h2 {
    font-size: 2rem;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
}

p {
    line-height: 1.6;
}

</style>
""", unsafe_allow_html=True)

# Task F1.2: Glassmorphism Card System
st.markdown("""
<style>

.glass-card {
    background: rgba(28, 37, 54, 0.7);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 24px;
    border: 1px solid rgba(76, 201, 240, 0.2);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
    border-color: rgba(76, 201, 240, 0.4);
}

.section-title {
    font-size: 28px;
    font-weight: 600;
    margin-bottom: 10px;
    color: #E0E7FF;
}

.sub-text {
    color: #94A3B8;
    font-size: 14px;
    line-height: 1.5;
}

.feature-icon {
    font-size: 2rem;
    margin-bottom: 8px;
}

</style>
""", unsafe_allow_html=True)

st.title("CIVISIM — Policy Simulation Dashboard")
st.markdown("Analyze how policies impact a synthetic society.")
st.divider()

# ================================================================
# HERO SECTION — Premium SaaS Style (Task F1.3)
# ================================================================
st.markdown("""
<div style="margin-top: 60px; text-align: center; margin-bottom: 80px;">

<h1 style="font-size: 52px; line-height: 1.2; margin-bottom: 20px;">
CIVISIM — AI-Powered Synthetic Society Simulator
</h1>

<p style="color: #94A3B8; font-size: 20px; max-width: 700px; margin: 0 auto; line-height: 1.6;">
Test public policies on thousands of virtual citizens before they affect the real world.
</p>

</div>
""", unsafe_allow_html=True)

# ================================================================
# FEATURE CARDS — Premium Design (Task F1.4)
# ================================================================
col1, col2, col3 = st.columns(3)

feature_cards = [
    ("🧠 Realistic Reactions", "AI simulates authentic human behavior"),
    ("⏳ Time Evolution", "Track policy impact across multiple time steps"),
    ("📊 Instant Insights", "Understand societal impact in seconds")
]

for col, (title, desc) in zip([col1, col2, col3], feature_cards):
    with col:
        st.markdown(f"""
        <div class="glass-card">
            <h3 style="margin-top: 0; margin-bottom: 12px; font-size: 18px;">{title}</h3>
            <p class="sub-text">{desc}</p>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ================================================================
# PHASE F-ULTRA 2: PROFESSIONAL DASHBOARD LAYOUT
# ================================================================

# Task F2.1: Create Professional 3-Column Grid Structure
st.markdown("""
<style>

/* Enhanced micro-interactions for all cards */
.glass-card {
    background: rgba(28, 37, 54, 0.7);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 24px;
    border: 1px solid rgba(76, 201, 240, 0.2);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
    transform: translateY(-6px) scale(1.01);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
    border-color: rgba(76, 201, 240, 0.4);
}

/* Metric card emphasis */
.metric-card-large h2 {
    font-size: 3rem;
    color: #4CC9F0;
    margin: 10px 0;
    font-weight: 700;
}

.metric-card-large p {
    color: #94A3B8;
    margin: 0;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

</style>
""", unsafe_allow_html=True)

st.markdown("## 🚀 Live Simulation Dashboard")

left, center, right = st.columns([1.2, 2.5, 1.3])

# ================================================================
# TASK F2.2: LEFT PANEL — SIMULATION CONTROL
# ================================================================
with left:
    st.markdown("""
    <div class="glass-card">
    <h3 style="margin-top: 0;">⚙️ Simulation Setup</h3>
    <p class="sub-text">Configure your experiment</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")  # Spacing
    
    citizens = st.slider("Number of Citizens", 1000, 50000, 10000, key="left_citizens")
    
    st.markdown("")  # Spacing
    
    steps = st.slider("Time Steps", 5, 50, 20, key="left_steps")
    
    st.markdown("")  # Spacing
    
    col_btn, col_empty = st.columns([1, 0.2])
    with col_btn:
        run_btn = st.button("Run Simulation 🚀", use_container_width=True)

# ================================================================
# TASK F2.3: CENTER PANEL — MAIN VISUALIZATION
# ================================================================
with center:
    st.markdown("""
    <div class="glass-card">
    <h3 style="margin-top: 0;">📈 Society Evolution Over Time</h3>
    <p class="sub-text">
    This graph shows how happiness, support, and income evolve after policy application.
    </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create professional Plotly visualization
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        y=[1, 2, 3, 4, 5],
        mode='lines',
        name='Happiness',
        line=dict(color='#4CC9F0', width=3),
        hovertemplate='<b>Happiness</b><br>Step: %{x}<br>Value: %{y:.2f}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        y=[1.2, 2.1, 3.3, 4.2, 5.1],
        mode='lines',
        name='Policy Support',
        line=dict(color='#7C3AED', width=3),
        hovertemplate='<b>Policy Support</b><br>Step: %{x}<br>Value: %{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified',
        margin=dict(l=10, r=10, t=20, b=10),
        height=400,
        font=dict(family="Inter, sans-serif", color="#E0E7FF"),
        xaxis=dict(
            gridcolor='rgba(76, 201, 240, 0.1)',
            zeroline=False
        ),
        yaxis=dict(
            gridcolor='rgba(76, 201, 240, 0.1)',
            zeroline=False
        ),
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor='rgba(0, 0, 0, 0.5)',
            bordercolor='rgba(76, 201, 240, 0.2)',
            borderwidth=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ================================================================
# TASK F2.4: RIGHT PANEL — KEY METRICS WITH EMPHASIS
# ================================================================
with right:
    st.markdown("""
    <div class="glass-card">
    <h3 style="margin-top: 0;">📊 Key Results</h3>
    <p class="sub-text">Instant insights</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")  # Spacing
    
    # Metric 1: Happiness
    st.markdown("""
    <div class="glass-card metric-card-large">
    <h2>0.72</h2>
    <p>Average Happiness</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")  # Spacing
    
    # Metric 2: Support
    st.markdown("""
    <div class="glass-card metric-card-large">
    <h2>68%</h2>
    <p>Policy Support</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")  # Spacing
    
    # Metric 3: Income
    st.markdown("""
    <div class="glass-card metric-card-large">
    <h2>₹45K</h2>
    <p>Avg Income</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ================================================================
# EXPLAINABILITY & STORY SECTION (Phase F4)
# ================================================================

# ================================================================
# SECTION: HOW IT WORKS (Phase F4.1)
# ================================================================
how_it_works_section = st.container()

with how_it_works_section:
    st.markdown("## How CIVISIM Works")
    
    steps = [
        "📋 Define Policy",
        "👥 Generate Population",
        "🤖 AI Reactions",
        "🧠 Neural Scaling",
        "⏱️ Time Simulation"
    ]
    
    cols = st.columns(5)
    
    for col, step in zip(cols, steps):
        with col:
            st.markdown(f"""
            <div class="glass-card">
            <p style="text-align: center; margin: 0; font-weight: 600;">{step}</p>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# ================================================================
# SECTION: CITIZEN EXPLORER (Phase F4.2)
# ================================================================
citizen_explorer_section = st.container()

with citizen_explorer_section:
    st.markdown("## Citizen Explorer")
    st.caption("Meet one of the virtual citizens in your simulation")
    
    st.markdown("""
    <div class="card">
    <h4>👤 Citizen Profile</h4>
    <p><strong>Age:</strong> 25</p>
    <p><strong>Occupation:</strong> Student</p>
    <p><strong>Income:</strong> ₹20,000</p>
    <p><strong>Location:</strong> Rural</p>
    <p><strong>Traits:</strong> Open, Moderate Risk Tolerance</p>
    <p><strong>Policy Support:</strong> 0.68 (Strong Support)</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ================================================================
# SECTION: CITIZEN DIARIES (Phase F4.3)
# ================================================================
diary_entries_section = st.container()

with diary_entries_section:
    st.markdown("## Citizen Diaries")
    st.caption("First-person narratives from the synthetic society")
    
    st.markdown("""
    <div class="card">
    <h4>💭 Diary Entry</h4>
    <p><em>"I'm feeling hopeful today. The new scholarship program will help me continue my education without burdening my family. This could change everything for me."</em></p>
    <p style="margin-top: 10px; font-size: 0.9em;"><strong>Emotion Shift:</strong> +0.35 happiness, +0.42 support</p>
    </div>
    """, unsafe_allow_html=True)

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
        # ================================================================
        # SIMULATION EXECUTION SECTION (Phase F1: Layout Containers)
        # ================================================================
        simulation_section = st.container()
        
        with simulation_section:
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

        # ================================================================
        # DASHBOARD SECTIONS (Phase F1: Layout Containers)
        # ================================================================
        
        # SECTION 1: Policy Context
        policy_context_section = st.container()
        with policy_context_section:
            st.markdown("### Situation Room")
            st.subheader("Policy Context")
            ctx_col1, ctx_col2 = st.columns(2)
            with ctx_col1:
                st.write("**Domain:**", parsed_policy["domain"].upper())
            with ctx_col2:
                st.write("**Relevant Attributes:**", ", ".join(attributes) if attributes else "None detected")

        # SECTION 2: Executive Summary
        executive_summary_section = st.container()
        with executive_summary_section:
            st.divider()
            st.markdown("### Executive Summary")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Avg Happiness",  round(metrics["happiness"][-1], 3))
            kpi2.metric("Policy Support", round(metrics["support"][-1], 3))
            kpi3.metric("Avg Income",     f"₹{int(metrics['income'][-1]):,}")
            kpi4.metric("Population",     f"{len(population):,}")

        # SECTION 3: Population Analytics
        analytics_section = st.container()
        with analytics_section:
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

        # SECTION 4: Policy Trajectory
        trajectory_section = st.container()
        with trajectory_section:
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

        # SECTION 5: Individual Citizen Explorer (Phase F-ULTRA 3 — Task F3.1)
        citizen_lens_section = st.container()
        with citizen_lens_section:
            st.divider()
            st.markdown("## 🧑 Citizen Explorer")

            selected_id = st.slider("Select Citizen", 0, len(population) - 1, 0)
            citizen = population[selected_id]

            st.markdown(f"""
            <div class="glass-card">
            <h3 style="margin-top: 0;">👤 Citizen Profile</h3>
            <p><b>Age:</b> {citizen.age}</p>
            <p><b>Occupation:</b> {citizen.occupation}</p>
            <p><b>Income:</b> ₹{int(citizen.income):,}</p>
            <p><b>Location:</b> {citizen.location}</p>
            <hr style="border-color: rgba(76, 201, 240, 0.2);">
            <p><b>Traits:</b></p>
            <ul style="margin: 5px 0;">
            <li>Risk Tolerance: {round(citizen.traits.get('risk_tolerance', 0.5), 2)}</li>
            <li>Openness: {round(citizen.traits.get('openness', 0.5), 2)}</li>
            <li>Political Leaning: {round(citizen.traits.get('political_leaning', 0.5), 2)}</li>
            </ul>
            <hr style="border-color: rgba(76, 201, 240, 0.2);">
            <p><b>Policy Support:</b> {round(citizen.policy_support, 2)}</p>
            </div>
            """, unsafe_allow_html=True)

        # SECTION 6: Human Narratives
        narratives_section = st.container()
        with narratives_section:
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