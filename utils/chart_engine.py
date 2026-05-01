import plotly.graph_objects as go
import streamlit as st

def plot_synced_vitals(df):
    fig = go.Figure()

    # Heart Rate
    fig.add_trace(go.Scatter(
        x=df["meta.event_date"],
        y=df["vitals.vitals.heart_rate"],
        name="Heart Rate",
        line=dict(width=2)
    ))

    # SpO2
    fig.add_trace(go.Scatter(
        x=df["meta.event_date"],
        y=df["vitals.vitals.spo2"],
        name="SpO2",
        line=dict(width=2, dash="dot")
    ))

    # Highlight alerts
    alert_points = df[df["meta.alert"] == True]

    if not alert_points.empty:
        fig.add_vline(
            x=alert_points["meta.event_date"].iloc[-1],
            line_width=2,
            line_color="red"
        )

    fig.update_layout(
        xaxis_title="Event Time",
        yaxis_title="Value",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)
