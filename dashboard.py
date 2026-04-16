import dash
from dash import html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
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
import pandas as pd

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "CIVISIM - Policy Simulation Dashboard"

# Custom CSS for additional styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metatags%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=Sora:wght@500;600;700;800&display=swap" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            :root {
                --primary-gradient: linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #38bdf8 100%);
                --secondary-gradient: linear-gradient(135deg, #111f38 0%, #1e3a8a 100%);
                --success-gradient: linear-gradient(135deg, #0f4c81 0%, #0ea5e9 100%);
                --warning-gradient: linear-gradient(135deg, #1d4ed8 0%, #22d3ee 100%);
                --dark-bg: #06090f;
                --darker-bg: #03060d;
                --card-bg: rgba(9, 20, 37, 0.74);
                --border-color: rgba(110, 164, 248, 0.25);
                --text-primary: #eaf1ff;
                --text-secondary: #a8bddf;
                --shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                --shadow-hover: 0 12px 40px rgba(0, 0, 0, 0.4);
            }

            * {
                font-family: 'Manrope', sans-serif;
            }

            body {
                background: var(--dark-bg);
                color: var(--text-primary);
                background-image:
                    radial-gradient(circle at 18% 24%, rgba(56, 189, 248, 0.13) 0%, transparent 45%),
                    radial-gradient(circle at 82% 78%, rgba(59, 130, 246, 0.14) 0%, transparent 46%);
                min-height: 100vh;
            }

            .hero-section {
                background: var(--primary-gradient);
                border-radius: 20px;
                padding: 40px;
                margin-bottom: 30px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }

            .hero-section::after {
                content: '';
                position: absolute;
                right: -140px;
                top: -110px;
                width: 320px;
                height: 320px;
                border-radius: 50%;
                background: radial-gradient(circle, rgba(186, 230, 253, 0.22) 0%, rgba(186, 230, 253, 0) 70%);
                pointer-events: none;
            }

            .hero-section::before {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: repeating-conic-gradient(
                    from 0deg,
                    transparent 0deg 90deg,
                    rgba(255, 255, 255, 0.05) 90deg 180deg
                );
                animation: rotate 20s linear infinite;
            }

            @keyframes rotate {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            .hero-title {
                font-size: 3.5rem;
                font-weight: 700;
                font-family: 'Sora', sans-serif;
                margin-bottom: 10px;
                position: relative;
                z-index: 1;
            }

            .hero-subtitle {
                font-size: 1.2rem;
                opacity: 0.9;
                position: relative;
                z-index: 1;
            }

            .card-custom {
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 20px;
                box-shadow: var(--shadow);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                backdrop-filter: blur(10px);
                position: relative;
                overflow: hidden;
            }

            .card-custom::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: var(--primary-gradient);
            }

            .card-custom:hover {
                transform: translateY(-5px);
                box-shadow: var(--shadow-hover);
                border-color: rgba(56, 189, 248, 0.58);
            }

            .metric-card {
                background: var(--primary-gradient);
                color: white;
                border-radius: 15px;
                padding: 25px;
                text-align: center;
                position: relative;
                overflow: hidden;
                transition: all 0.3s ease;
            }

            .metric-card::before {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                transition: all 0.3s ease;
            }

            .metric-card:hover::before {
                transform: scale(1.5);
            }

            .metric-value {
                font-size: 2rem;
                font-weight: 700;
                margin-bottom: 5px;
            }

            .metric-label {
                font-size: 0.9rem;
                opacity: 0.9;
                font-weight: 500;
            }

            .policy-input {
                background: rgba(255, 255, 255, 0.05);
                border: 2px solid var(--border-color);
                border-radius: 15px;
                color: var(--text-primary);
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .policy-input:focus {
                border-color: #38bdf8;
                box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.25);
                background: rgba(255, 255, 255, 0.08);
            }

            .btn-custom {
                background: var(--primary-gradient);
                border: none;
                border-radius: 30px;
                padding: 15px 40px;
                font-weight: 600;
                font-size: 1.1rem;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
                box-shadow: 0 6px 18px rgba(37, 99, 235, 0.36);
            }

            .btn-custom::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                transition: left 0.5s;
            }

            .btn-custom:hover::before {
                left: 100%;
            }

            .btn-custom:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 28px rgba(14, 165, 233, 0.44);
            }

            .slider-container {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }

            .chart-container {
                background: var(--card-bg);
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
                border: 1px solid var(--border-color);
                transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
            }

            .chart-container:hover {
                transform: translateY(-2px);
                border-color: rgba(56, 189, 248, 0.52);
                box-shadow: 0 14px 34px rgba(2, 8, 23, 0.35);
            }

            .loading-spinner {
                display: inline-block;
                width: 40px;
                height: 40px;
                border: 3px solid rgba(255,255,255,0.1);
                border-radius: 50%;
                border-top-color: #38bdf8;
                animation: spin 1s ease-in-out infinite;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            .fade-in {
                animation: fadeIn 0.5s ease-in;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .pulse {
                animation: pulse 2s infinite;
            }

            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }

            .glass-effect {
                backdrop-filter: blur(20px);
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }

            .icon-large {
                font-size: 2rem;
                margin-bottom: 10px;
            }

            .section-title {
                font-size: 1.8rem;
                font-weight: 600;
                margin-bottom: 20px;
                color: var(--text-primary);
            }

            .stat-card {
                background: var(--card-bg);
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 15px;
                border: 1px solid var(--border-color);
                transition: all 0.3s ease;
            }

            .stat-card:hover {
                border-color: rgba(56, 189, 248, 0.52);
                transform: translateY(-2px);
            }

            @media (max-width: 992px) {
                .hero-section {
                    padding: 30px 22px;
                }

                .hero-title {
                    font-size: 2.5rem;
                }
            }

            @media (max-width: 576px) {
                .hero-section {
                    border-radius: 16px;
                    margin-bottom: 22px;
                }

                .hero-title {
                    font-size: 2rem;
                }

                .hero-subtitle {
                    font-size: 1rem;
                }

                .btn-custom {
                    width: 100%;
                    padding: 14px 18px;
                    border-radius: 16px;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# App Layout
app.layout = dbc.Container([
    # Hero Section
    dbc.Row([
        dbc.Col([
            html.Div([
                html.I(className="fas fa-brain icon-large"),
                html.H1("🎯 CIVISIM", className="hero-title"),
                html.P("Advanced AI-Powered Policy Simulation & Social Impact Analysis", className="hero-subtitle"),
                html.P("Simulate real-world policy impacts on synthetic populations with cutting-edge machine learning", className="text-center mt-3", style={"fontSize": "1rem", "opacity": "0.8"})
            ], className="hero-section")
        ])
    ]),

    # Policy Input Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-cogs me-2"),
                    html.H4("Policy Configuration", className="d-inline mb-0")
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-file-alt me-2"),
                                "Policy Description"
                            ], className="fw-bold mb-3"),
                            dcc.Textarea(
                                id='policy-input',
                                placeholder="Example: Increase scholarships for rural OBC students and waive tuition fees for families below ₹3 lakh annual income",
                                style={'width': '100%', 'height': 120, 'borderRadius': '15px', 'padding': '20px', 'fontSize': '1rem'},
                                className="policy-input form-control"
                            )
                        ], width=8),
                        dbc.Col([
                            html.Div([
                                html.Label([
                                    html.I(className="fas fa-sliders-h me-2"),
                                    "Simulation Parameters"
                                ], className="fw-bold mb-3"),
                                html.Div([
                                    html.Label("Simulation Steps:", className="small fw-semibold"),
                                    dcc.Slider(
                                        id='steps-slider',
                                        min=5, max=50, value=10, step=5,
                                        marks={i: f'{i}' for i in range(5, 51, 10)},
                                        className="mb-4"
                                    ),
                                ], className="mb-3"),
                                html.Div([
                                    html.Label("LLM Sample Size:", className="small fw-semibold"),
                                    dcc.Slider(
                                        id='sample-slider',
                                        min=50, max=200, value=100, step=50,
                                        marks={50: '50', 100: '100', 150: '150', 200: '200'},
                                        className="mb-4"
                                    ),
                                ], className="mb-3"),
                                dbc.Button([
                                    html.I(className="fas fa-rocket me-2"),
                                    "Run Simulation"
                                ], id="run-btn", className="btn-custom w-100")
                            ], className="slider-container")
                        ], width=4)
                    ])
                ])
            ], className="card-custom mb-4")
        ])
    ]),

    # Loading and Results Section
    dcc.Loading(
        id="loading",
        type="circle",
        color="#38bdf8",
        children=[
            html.Div(id="results-container", className="fade-in")
        ]
    ),

    # Permanent Citizen Explorer Section (always present but hidden when no data)
    html.Div(id="citizen-explorer-container", style={"display": "none"}, children=[
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-user-astronaut me-2"),
                        html.H4("Individual Citizen Analysis", className="d-inline mb-0")
                    ]),
                    dbc.CardBody([
                        html.P("Explore individual citizens and their unique responses to the policy", className="text-muted mb-4"),
                        html.Label([
                            html.I(className="fas fa-search me-2"),
                            "Select Citizen ID:"
                        ], className="fw-bold mb-3"),
                        dcc.Slider(
                            id='citizen-slider',
                            min=0,
                            max=9999,  # Will be updated dynamically
                            value=0,
                            step=1,
                            className="mb-4"
                        ),
                        html.Div(id='citizen-details', className="fade-in")
                    ])
                ], className="card-custom mb-4")
            ])
        ])
    ]),

    # Permanent Narratives Section (always present but hidden when no data)
    html.Div(id="narratives-container", style={"display": "none"}, children=[
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-comments me-2"),
                        html.H4("AI-Generated Citizen Stories", className="d-inline mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-info-circle me-2 text-info"),
                            html.Span("Showing AI-generated reactions from the sample population.", id="narratives-info")
                        ], className="alert alert-info mb-4", style={"borderRadius": "10px"}),
                        html.Div(id='narratives-content', className="fade-in")
                    ])
                ], className="card-custom")
            ])
        ])
    ]),

    # Store for simulation data
    dcc.Store(id='simulation-data'),
    dcc.Store(id='population-data'),
    dcc.Store(id='reactions-data')

], fluid=True, className="p-4")

# Callback for running simulation
@app.callback(
    [Output('results-container', 'children'),
     Output('citizen-explorer-container', 'style'),
     Output('narratives-container', 'style'),
     Output('simulation-data', 'data'),
     Output('population-data', 'data'),
     Output('reactions-data', 'data')],
    [Input('run-btn', 'n_clicks')],
    [State('policy-input', 'value'),
     State('steps-slider', 'value'),
     State('sample-slider', 'value')]
)
def run_simulation_callback(n_clicks, policy, steps, sample_size):
    if n_clicks is None or not policy or not policy.strip():
        return [], {"display": "none"}, {"display": "none"}, None, None, None

    try:
        # Simulation logic (same as Streamlit version)
        parsed_policy = parse_policy(policy)
        attributes = map_policy_to_attributes(parsed_policy)
        population = generate_population(10000, attributes)

        reactions, sample_population = simulate_population_reactions(
            population, policy, sample_size=sample_size
        )

        X, y = create_training_data(sample_population, reactions, parsed_policy)
        model, mean, std = train_model(X, y, epochs=100)

        policy_encoding = encode_policy(parsed_policy)[0]
        metrics = run_simulation(
            population, model, steps, mean, std, policy_encoding
        )

        # Convert population to dict for storage
        population_dict = [{
            'cid': c.cid,
            'age': c.age,
            'income': c.income,
            'occupation': c.occupation,
            'caste': c.caste,
            'location': c.location,
            'happiness': c.happiness,
            'policy_support': c.policy_support,
            'traits': c.traits,
            'extra_attributes': c.extra_attributes
        } for c in population]

        # Create results layout
        results_layout = [

            # Success Message
            dbc.Row([
                dbc.Col([
                    dbc.Alert([
                        html.I(className="fas fa-check-circle me-2"),
                        f"Simulation completed successfully! Processed {len(population):,} citizens across {steps} time steps."
                    ], color="success", className="mb-4 fade-in", style={"borderRadius": "15px"})
                ])
            ]),

            # Policy Context
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-search me-2"),
                            html.H4("Policy Analysis", className="d-inline mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.I(className="fas fa-globe text-primary icon-large"),
                                        html.H5("Domain", className="mt-2"),
                                        html.P(parsed_policy["domain"].upper(), className="text-primary fw-bold mb-0")
                                    ], className="text-center stat-card")
                                ], width=4),
                                dbc.Col([
                                    html.Div([
                                        html.I(className="fas fa-cogs text-info icon-large"),
                                        html.H5("Mechanism", className="mt-2"),
                                        html.P(parsed_policy.get("mechanism", "N/A").upper(), className="text-info fw-bold mb-0")
                                    ], className="text-center stat-card")
                                ], width=4),
                                dbc.Col([
                                    html.Div([
                                        html.I(className="fas fa-brain text-warning icon-large"),
                                        html.H5("Parser", className="mt-2"),
                                        html.P(parsed_policy.get("parsed_by", "keyword").upper(), className="text-warning fw-bold mb-0")
                                    ], className="text-center stat-card")
                                ], width=4)
                            ], className="mb-3"),
                            html.Div([
                                html.I(className="fas fa-users me-2"),
                                html.Strong("Affected Groups:"),
                                html.P(", ".join(parsed_policy.get("affected_groups", ["None"])), className="mb-2 d-inline ms-2")
                            ], className="mb-2"),
                            html.Div([
                                html.I(className="fas fa-tags me-2"),
                                html.Strong("Relevant Attributes:"),
                                html.P(", ".join(attributes) if attributes else "None", className="mb-0 d-inline ms-2")
                            ])
                        ])
                    ], className="card-custom mb-4")
                ])
            ]),

            # Executive Summary
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-chart-line me-2"),
                            html.H4("Executive Summary", className="d-inline mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.I(className="fas fa-smile-beam text-success icon-large"),
                                        html.Div(f"{metrics['happiness'][-1]:.3f}", className="metric-value"),
                                        html.Div("Avg Happiness", className="metric-label")
                                    ], className="metric-card")
                                ], width=3),
                                dbc.Col([
                                    html.Div([
                                        html.I(className="fas fa-thumbs-up text-primary icon-large"),
                                        html.Div(f"{metrics['support'][-1]:.3f}", className="metric-value"),
                                        html.Div("Policy Support", className="metric-label")
                                    ], className="metric-card")
                                ], width=3),
                                dbc.Col([
                                    html.Div([
                                        html.I(className="fas fa-rupee-sign text-warning icon-large"),
                                        html.Div(f"₹{int(metrics['income'][-1]):,}", className="metric-value"),
                                        html.Div("Avg Income", className="metric-label")
                                    ], className="metric-card")
                                ], width=3),
                                dbc.Col([
                                    html.Div([
                                        html.I(className="fas fa-users text-info icon-large"),
                                        html.Div(f"{len(population):,}", className="metric-value"),
                                        html.Div("Population", className="metric-label")
                                    ], className="metric-card")
                                ], width=3)
                            ])
                        ])
                    ], className="card-custom mb-4")
                ])
            ]),

            # Population Analytics
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-chart-pie me-2"),
                            html.H4("Population Demographics", className="d-inline mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        dcc.Graph(
                                            id='occupation-chart',
                                            figure=create_occupation_chart(population),
                                            style={'height': '350px'}
                                        )
                                    ], className="chart-container")
                                ], width=6),
                                dbc.Col([
                                    html.Div([
                                        dcc.Graph(
                                            id='caste-chart',
                                            figure=create_caste_chart(population),
                                            style={'height': '350px'}
                                        )
                                    ], className="chart-container")
                                ], width=6)
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        dcc.Graph(
                                            id='income-chart',
                                            figure=create_income_chart(population),
                                            style={'height': '350px'}
                                        )
                                    ], className="chart-container")
                                ], width=6),
                                dbc.Col([
                                    html.Div([
                                        dcc.Graph(
                                            id='happiness-occupation-chart',
                                            figure=create_happiness_occupation_chart(population),
                                            style={'height': '350px'}
                                        )
                                    ], className="chart-container")
                                ], width=6)
                            ])
                        ])
                    ], className="card-custom mb-4")
                ])
            ]),

            # Policy Trajectory
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-chart-area me-2"),
                            html.H4("Policy Impact Timeline", className="d-inline mb-0")
                        ]),
                        dbc.CardBody([
                            html.P(f"Time-series analysis over {steps} simulation steps", className="text-muted mb-4"),
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        dcc.Graph(
                                            id='happiness-trend',
                                            figure=create_trend_chart(metrics['happiness'], "Happiness Trajectory", "Happiness"),
                                            style={'height': '300px'}
                                        )
                                    ], className="chart-container")
                                ], width=4),
                                dbc.Col([
                                    html.Div([
                                        dcc.Graph(
                                            id='support-trend',
                                            figure=create_trend_chart(metrics['support'], "Support Trajectory", "Support"),
                                            style={'height': '300px'}
                                        )
                                    ], className="chart-container")
                                ], width=4),
                                dbc.Col([
                                    html.Div([
                                        dcc.Graph(
                                            id='income-trend',
                                            figure=create_trend_chart(metrics['income'], "Income Trajectory", "Income (₹)"),
                                            style={'height': '300px'}
                                        )
                                    ], className="chart-container")
                                ], width=4)
                            ])
                        ])
                    ], className="card-custom mb-4")
                ])
            ])
        ]

        return results_layout, {"display": "block"}, {"display": "block"}, metrics, population_dict, reactions

    except Exception as e:
        return [
            dbc.Alert(f"Error running simulation: {str(e)}", color="danger", className="mt-3")
        ], {"display": "none"}, {"display": "none"}, None, None, None

# Helper functions for creating charts
def create_occupation_chart(population):
    occ_dist = occupation_distribution(population)
    fig = px.bar(
        x=list(occ_dist.keys()),
        y=list(occ_dist.values()),
        title="",
        labels={"x": "Occupation", "y": "Citizens"},
        color_discrete_sequence=['#38bdf8']
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title_font_size=16,
        title_font_color='white',
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            linecolor='rgba(255,255,255,0.2)'
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            linecolor='rgba(255,255,255,0.2)'
        ),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

def create_caste_chart(population):
    caste_dist = caste_distribution(population)
    fig = px.pie(
        names=list(caste_dist.keys()),
        values=list(caste_dist.values()),
        title="",
        color_discrete_sequence=['#38bdf8', '#3b82f6', '#2563eb', '#1d4ed8', '#0ea5e9']
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title_font_size=16,
        title_font_color='white',
        margin=dict(l=20, r=20, t=40, b=20)
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def create_income_chart(population):
    fig = px.histogram(
        income_list(population),
        nbins=30,
        title="",
        labels={"value": "Income (₹)", "count": "Citizens"},
        color_discrete_sequence=['#2563eb']
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title_font_size=16,
        title_font_color='white',
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            linecolor='rgba(255,255,255,0.2)'
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            linecolor='rgba(255,255,255,0.2)'
        ),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

def create_happiness_occupation_chart(population):
    groups = group_by_attribute(population, "occupation")
    group_happiness = group_average_happiness(groups)
    sorted_happiness = dict(
        sorted(group_happiness.items(), key=lambda item: item[1], reverse=True)
    )
    fig = px.bar(
        x=list(sorted_happiness.keys()),
        y=list(sorted_happiness.values()),
        title="",
        labels={"x": "Occupation", "y": "Avg Happiness"},
        color_discrete_sequence=['#0ea5e9']
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title_font_size=16,
        title_font_color='white',
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            linecolor='rgba(255,255,255,0.2)'
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            linecolor='rgba(255,255,255,0.2)'
        ),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

def create_trend_chart(data, title, y_label):
    line_color = '#38bdf8'
    if 'Support' in y_label:
        line_color = '#3b82f6'
    elif 'Income' in y_label:
        line_color = '#1d4ed8'

    fig = px.line(
        y=data,
        title="",
        labels={"index": "Step", "y": y_label}
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title_font_size=16,
        title_font_color='white',
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            linecolor='rgba(255,255,255,0.2)',
            title="Simulation Steps"
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            linecolor='rgba(255,255,255,0.2)',
            title=y_label
        ),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    fig.update_traces(
        line=dict(width=3, color=line_color),
        marker=dict(color=line_color),
        mode='lines+markers'
    )
    return fig

# Callback to update citizen slider max
@app.callback(
    Output('citizen-slider', 'max'),
    [Input('population-data', 'data')]
)
def update_slider_max(population_data):
    if population_data is None:
        return 9999
    return len(population_data) - 1
@app.callback(
    Output('citizen-details', 'children'),
    [Input('citizen-slider', 'value')],
    [State('population-data', 'data')]
)
def update_citizen_details(selected_id, population_data):
    if population_data is None or selected_id >= len(population_data):
        return dbc.Alert("No citizen data available", color="warning", className="text-center")

    citizen = population_data[selected_id]

    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-id-card me-2"),
                    f"Citizen Profile #{citizen['cid']}"
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.I(className="fas fa-birthday-cake text-primary me-2"),
                                html.Strong("Age:"),
                                html.Span(f" {citizen['age']} years", className="ms-2")
                            ], className="mb-3")
                        ], width=6),
                        dbc.Col([
                            html.Div([
                                html.I(className="fas fa-map-marker-alt text-info me-2"),
                                html.Strong("Location:"),
                                html.Span(f" {citizen['location']}", className="ms-2")
                            ], className="mb-3")
                        ], width=6)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.I(className="fas fa-briefcase text-success me-2"),
                                html.Strong("Occupation:"),
                                html.Span(f" {citizen['occupation']}", className="ms-2")
                            ], className="mb-3")
                        ], width=6),
                        dbc.Col([
                            html.Div([
                                html.I(className="fas fa-users text-warning me-2"),
                                html.Strong("Caste:"),
                                html.Span(f" {citizen['caste']}", className="ms-2")
                            ], className="mb-3")
                        ], width=6)
                    ]),
                    html.Div([
                        html.I(className="fas fa-rupee-sign text-warning me-2"),
                        html.Strong("Income:"),
                        html.Span(f" ₹{int(citizen['income']):,} per month", className="ms-2 text-success fw-bold")
                    ], className="mb-3")
                ])
            ], className="stat-card mb-3")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-brain me-2"),
                    "Policy Response & Personality"
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.I(className="fas fa-smile-beam text-success me-2"),
                                html.Strong("Happiness:"),
                                html.Span(f" {citizen['happiness']:.3f}", className="ms-2 badge bg-success")
                            ], className="mb-3")
                        ], width=6),
                        dbc.Col([
                            html.Div([
                                html.I(className="fas fa-thumbs-up text-primary me-2"),
                                html.Strong("Policy Support:"),
                                html.Span(f" {citizen['policy_support']:.3f}", className="ms-2 badge bg-primary")
                            ], className="mb-3")
                        ], width=6)
                    ]),
                    html.Div([
                        html.I(className="fas fa-dna text-info me-2"),
                        html.Strong("Personality Traits:"),
                        html.Div([
                            html.Span(trait, className="badge bg-info me-1 mb-1") for trait in citizen.get('traits', [])
                        ], className="ms-2 mt-2")
                    ], className="mb-3"),
                    html.Div([
                        html.I(className="fas fa-plus-circle text-secondary me-2"),
                        html.Strong("Extra Attributes:"),
                        html.Pre(str(citizen.get('extra_attributes', {})), className="ms-2 mt-2 small text-muted bg-light p-2 rounded")
                    ])
                ])
            ], className="stat-card")
        ], width=6)
    ])

# Callback for narratives
@app.callback(
    [Output('narratives-content', 'children'),
     Output('narratives-info', 'children')],
    [Input('reactions-data', 'data'),
     Input('population-data', 'data')]
)
def update_narratives(reactions_data, population_data):
    if reactions_data is None or population_data is None:
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            "No citizen narratives available yet. Run a simulation first."
        ], color="info", className="text-center"), "Showing AI-generated reactions from the sample population."

    narratives = []
    for i, reaction in enumerate(reactions_data[:5]):
        citizen = population_data[i]
        narratives.append(
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-user-circle me-2 text-primary"),
                    html.Strong(f"Citizen {i + 1}"),
                    html.Span(f" • {citizen['age']}yr • {citizen['occupation']}", className="text-muted ms-2 small")
                ], className="bg-light"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.I(className="fas fa-users text-warning me-2"),
                                html.Small(f"{citizen['caste']} • {citizen['location']}", className="text-muted")
                            ], className="mb-2"),
                            html.Div([
                                html.I(className="fas fa-rupee-sign text-success me-2"),
                                html.Small(f"₹{int(citizen['income']):,} monthly income", className="text-muted")
                            ])
                        ], width=8),
                        dbc.Col([
                            html.Div([
                                dbc.Badge([
                                    html.I(className="fas fa-smile-beam me-1"),
                                    f"{reaction.get('happiness_change', 0):.3f}"
                                ], color="success", className="me-1 mb-1"),
                                dbc.Badge([
                                    html.I(className="fas fa-thumbs-up me-1"),
                                    f"{reaction.get('support_change', 0):.3f}"
                                ], color="primary", className="me-1 mb-1"),
                                dbc.Badge([
                                    html.I(className="fas fa-rupee-sign me-1"),
                                    f"₹{int(reaction.get('income_change', 0)):,}"
                                ], color="warning")
                            ], className="text-end")
                        ], width=4)
                    ], className="mb-3"),
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-quote-left text-muted me-2"),
                            html.Span(reaction.get("diary_entry", "No personal reflection available."), className="fst-italic")
                        ])
                    ], className="bg-light border-0")
                ])
            ], className="mb-4 stat-card")
        )

    return narratives, f"Showing 5 of {len(reactions_data)} LLM-simulated reactions from the sample population."

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)