import streamlit as st

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
    st.warning("Simulation engine not implemented yet.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Average Happiness")
    st.line_chart([0, 1, 2, 3])

with col2:
    st.subheader("Policy Support")
    st.line_chart([3, 2, 5, 4])
