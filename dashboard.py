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
        <style>
            .card-custom {
                border-radius: 15px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: transform 0.2s;
            }
            .card-custom:hover {
                transform: translateY(-2px);
            }
            .metric-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
            }
            .policy-input {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
            .btn-custom {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                border-radius: 25px;
                padding: 12px 30px;
                font-weight: 600;
                transition: all 0.3s;
            }
            .btn-custom:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
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
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("🎯 CIVISIM", className="text-center mb-4", style={"color": "#667eea", "fontWeight": "bold"}),
            html.P("Advanced Policy Simulation & Social Impact Analysis", className="text-center text-muted mb-4")
        ])
    ]),

    # Policy Input Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("📋 Policy Configuration", className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Policy Description", className="fw-bold"),
                            dcc.Textarea(
                                id='policy-input',
                                placeholder="Example: Increase scholarships for rural OBC students and waive tuition fees for families below ₹3 lakh annual income",
                                style={'width': '100%', 'height': 120, 'borderRadius': '10px', 'padding': '15px'},
                                className="policy-input"
                            )
                        ], width=8),
                        dbc.Col([
                            html.Label("Simulation Parameters", className="fw-bold"),
                            html.Br(),
                            html.Label("Steps:", className="small"),
                            dcc.Slider(
                                id='steps-slider',
                                min=5, max=50, value=10, step=5,
                                marks={i: str(i) for i in range(5, 51, 10)}
                            ),
                            html.Br(),
                            html.Label("LLM Sample Size:", className="small"),
                            dcc.Slider(
                                id='sample-slider',
                                min=50, max=200, value=100, step=50,
                                marks={50: '50', 100: '100', 150: '150', 200: '200'}
                            ),
                            html.Br(),
                            dbc.Button(
                                "🚀 Run Simulation",
                                id="run-btn",
                                color="primary",
                                size="lg",
                                className="btn-custom w-100 mt-3"
                            )
                        ], width=4)
                    ])
                ])
            ], className="card-custom mb-4")
        ])
    ]),

    # Loading and Results Section
    dcc.Loading(
        id="loading",
        type="default",
        children=[
            html.Div(id="results-container")
        ]
    ),

    # Store for simulation data
    dcc.Store(id='simulation-data'),
    dcc.Store(id='population-data'),
    dcc.Store(id='reactions-data')

], fluid=True, className="p-4")

# Callback for running simulation
@app.callback(
    [Output('results-container', 'children'),
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
        return [], None, None, None

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

            # Policy Context
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("🎯 Policy Context", className="mb-0")),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Strong("Domain:"),
                                    html.P(parsed_policy["domain"].upper(), className="text-primary mb-2")
                                ], width=4),
                                dbc.Col([
                                    html.Strong("Mechanism:"),
                                    html.P(parsed_policy.get("mechanism", "N/A").upper(), className="text-info mb-2")
                                ], width=4),
                                dbc.Col([
                                    html.Strong("Parsed by:"),
                                    html.P(parsed_policy.get("parsed_by", "keyword").upper(), className="text-warning mb-2")
                                ], width=4)
                            ]),
                            html.Strong("Affected Groups:"),
                            html.P(", ".join(parsed_policy.get("affected_groups", ["None"])), className="mb-2"),
                            html.Strong("Relevant Attributes:"),
                            html.P(", ".join(attributes) if attributes else "None")
                        ])
                    ], className="card-custom mb-4")
                ])
            ]),

            # Executive Summary
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("📊 Executive Summary", className="mb-0")),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H3(f"{metrics['happiness'][-1]:.3f}", className="text-center text-success"),
                                            html.P("Avg Happiness", className="text-center mb-0")
                                        ])
                                    ], className="metric-card mb-3")
                                ], width=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H3(f"{metrics['support'][-1]:.3f}", className="text-center text-primary"),
                                            html.P("Policy Support", className="text-center mb-0")
                                        ])
                                    ], className="metric-card mb-3")
                                ], width=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H3(f"₹{int(metrics['income'][-1]):,}", className="text-center text-warning"),
                                            html.P("Avg Income", className="text-center mb-0")
                                        ])
                                    ], className="metric-card mb-3")
                                ], width=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H3(f"{len(population):,}", className="text-center text-info"),
                                            html.P("Population", className="text-center mb-0")
                                        ])
                                    ], className="metric-card mb-3")
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
                        dbc.CardHeader(html.H4("👥 Population Analytics", className="mb-0")),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dcc.Graph(
                                        id='occupation-chart',
                                        figure=create_occupation_chart(population),
                                        style={'height': '400px'}
                                    )
                                ], width=6),
                                dbc.Col([
                                    dcc.Graph(
                                        id='caste-chart',
                                        figure=create_caste_chart(population),
                                        style={'height': '400px'}
                                    )
                                ], width=6)
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    dcc.Graph(
                                        id='income-chart',
                                        figure=create_income_chart(population),
                                        style={'height': '400px'}
                                    )
                                ], width=6),
                                dbc.Col([
                                    dcc.Graph(
                                        id='happiness-occupation-chart',
                                        figure=create_happiness_occupation_chart(population),
                                        style={'height': '400px'}
                                    )
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
                        dbc.CardHeader(html.H4("📈 Policy Trajectory", className="mb-0")),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dcc.Graph(
                                        id='happiness-trend',
                                        figure=create_trend_chart(metrics['happiness'], "Happiness Over Time", "Happiness"),
                                        style={'height': '300px'}
                                    )
                                ], width=4),
                                dbc.Col([
                                    dcc.Graph(
                                        id='support-trend',
                                        figure=create_trend_chart(metrics['support'], "Policy Support Over Time", "Support"),
                                        style={'height': '300px'}
                                    )
                                ], width=4),
                                dbc.Col([
                                    dcc.Graph(
                                        id='income-trend',
                                        figure=create_trend_chart(metrics['income'], "Income Over Time", "Income (₹)"),
                                        style={'height': '300px'}
                                    )
                                ], width=4)
                            ])
                        ])
                    ], className="card-custom mb-4")
                ])
            ]),

            # Citizen Explorer
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("🔍 Citizen Explorer", className="mb-0")),
                        dbc.CardBody([
                            html.Label("Select Citizen ID:"),
                            dcc.Slider(
                                id='citizen-slider',
                                min=0,
                                max=9999,  # Will be updated dynamically
                                value=0,
                                step=1
                            ),
                            html.Div(id='citizen-details')
                        ])
                    ], className="card-custom mb-4")
                ])
            ]),

            # Human Narratives
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("📖 Human Narratives", className="mb-0")),
                        dbc.CardBody([
                            html.P(f"Showing 5 of {len(reactions)} LLM-simulated reactions.", className="text-muted"),
                            html.Div(id='narratives-content')
                        ])
                    ], className="card-custom")
                ])
            ])
        ]

        return results_layout, metrics, population_dict, reactions

    except Exception as e:
        return [
            dbc.Alert(f"Error running simulation: {str(e)}", color="danger", className="mt-3")
        ], None, None, None

# Helper functions for creating charts
def create_occupation_chart(population):
    occ_dist = occupation_distribution(population)
    fig = px.bar(
        x=list(occ_dist.keys()),
        y=list(occ_dist.values()),
        title="Occupation Distribution",
        labels={"x": "Occupation", "y": "Citizens"},
        color_discrete_sequence=['#667eea']
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    return fig

def create_caste_chart(population):
    caste_dist = caste_distribution(population)
    fig = px.pie(
        names=list(caste_dist.keys()),
        values=list(caste_dist.values()),
        title="Caste Distribution"
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    return fig

def create_income_chart(population):
    fig = px.histogram(
        income_list(population),
        nbins=30,
        title="Income Distribution",
        labels={"value": "Income (₹)", "count": "Citizens"},
        color_discrete_sequence=['#764ba2']
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
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
        title="Happiness by Occupation",
        labels={"x": "Occupation", "y": "Avg Happiness"},
        color_discrete_sequence=['#f093fb']
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
    )
    return fig

def create_trend_chart(data, title, y_label):
    fig = px.line(
        y=data,
        title=title,
        labels={"index": "Step", "y": y_label}
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white'
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
        return "No data available"

    citizen = population_data[selected_id]

    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5(f"Citizen {citizen['cid']}", className="card-title"),
                    html.P(f"Age: {citizen['age']}"),
                    html.P(f"Income: ₹{int(citizen['income']):,}"),
                    html.P(f"Occupation: {citizen['occupation']}"),
                    html.P(f"Caste: {citizen['caste']}"),
                    html.P(f"Location: {citizen['location']}")
                ])
            ], className="mb-3")
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.P(f"Happiness: {citizen['happiness']:.3f}"),
                    html.P(f"Policy Support: {citizen['policy_support']:.3f}"),
                    html.Strong("Traits:"),
                    html.P(", ".join(citizen.get('traits', []))),
                    html.Strong("Extra Attributes:"),
                    html.P(str(citizen.get('extra_attributes', {})))
                ])
            ])
        ], width=6)
    ])

# Callback for narratives
@app.callback(
    Output('narratives-content', 'children'),
    [Input('reactions-data', 'data'),
     Input('population-data', 'data')]
)
def update_narratives(reactions_data, population_data):
    if reactions_data is None or population_data is None:
        return "No narratives available"

    narratives = []
    for i, reaction in enumerate(reactions_data[:5]):
        citizen = population_data[i]
        narratives.append(
            dbc.Card([
                dbc.CardBody([
                    html.H6(f"Citizen {i + 1} — {citizen['age']}yr {citizen['occupation']}, {citizen['caste']}, {citizen['location']}, ₹{int(citizen['income']):,}/month"),
                    html.P(reaction.get("diary_entry", "No entry available.")),
                    dbc.Row([
                        dbc.Col([
                            dbc.Badge(f"Δ Happiness: {reaction.get('happiness_change', 0):.3f}", color="success", className="me-2")
                        ]),
                        dbc.Col([
                            dbc.Badge(f"Δ Support: {reaction.get('support_change', 0):.3f}", color="primary", className="me-2")
                        ]),
                        dbc.Col([
                            dbc.Badge(f"Δ Income: ₹{int(reaction.get('income_change', 0)):,}", color="warning")
                        ])
                    ])
                ])
            ], className="mb-3")
        )

    return narratives

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)