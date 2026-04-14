# CiviSim Dashboard

A modern, aesthetic web dashboard for policy simulation and social impact analysis built with Dash.

## Features

- 🎯 **Modern UI**: Beautiful dark theme with gradient cards and smooth animations
- 📊 **Interactive Visualizations**: Plotly-powered charts for population analytics and policy trajectories
- 🔍 **Citizen Explorer**: Interactive citizen selection and detailed profiles
- 📖 **Human Narratives**: LLM-generated citizen reactions and stories
- 🚀 **Real-time Simulation**: Live policy impact simulation with progress tracking

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Dashboard

### Option 1: Development Mode
```bash
python dashboard.py
```

### Option 2: Production Mode
```bash
gunicorn dashboard:app -b 0.0.0.0:8050
```

The dashboard will be available at `http://localhost:8050`

## Usage

1. **Enter Policy**: Describe your policy in natural language
2. **Configure Parameters**:
   - **Simulation Steps**: Number of time steps to simulate (5-50)
   - **LLM Sample Size**: Number of citizens to send to LLM for reactions (50-200)
3. **Run Simulation**: Click the "🚀 Run Simulation" button
4. **Explore Results**:
   - **Policy Context**: Parsed policy information and affected groups
   - **Executive Summary**: Key metrics and KPIs
   - **Population Analytics**: Distribution charts and demographics
   - **Policy Trajectory**: Time-series trends over simulation steps
   - **Citizen Explorer**: Individual citizen profiles and attributes
   - **Human Narratives**: AI-generated citizen reactions

## Architecture

The dashboard is built with:
- **Dash**: Web framework for Python
- **Dash Bootstrap Components**: Modern UI components
- **Plotly**: Interactive data visualizations
- **Custom CSS**: Gradient backgrounds and smooth animations

## Comparison with Streamlit Version

| Feature | Streamlit | Dash |
|---------|-----------|------|
| UI Theme | Basic | Modern dark theme with gradients |
| Layout | Simple columns | Responsive Bootstrap grid |
| Styling | Limited | Extensive custom CSS |
| Interactivity | Basic | Advanced callbacks and state management |
| Performance | Good | Excellent for complex dashboards |
| Deployment | Streamlit Cloud | Any WSGI server |

## API Endpoints

The dashboard integrates with your existing CiviSim backend:
- Population generation
- Policy parsing and mapping
- LLM interface for citizen reactions
- Neural network training
- Simulation engine

## Customization

The dashboard can be easily customized by modifying:
- `app.index_string`: Custom HTML/CSS
- Color schemes in chart functions
- Bootstrap theme in `dbc.themes.DARKLY`
- Layout components in `app.layout`