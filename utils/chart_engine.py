import plotly.graph_objects as go
import streamlit as st
import pandas as pd

def plot_synced_vitals(df: pd.DataFrame):
    if df.empty:
        st.warning("No data available for plotting.")
        return

    try:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df["meta.event_date"],
            y=df["vitals.heart_rate"],
            name="Heart Rate (BPM)",
            line=dict(width=2, color="#e74c3c")
        ))

        fig.add_trace(go.Scatter(
            x=df["meta.event_date"],
            y=df["vitals.spo2"],
            name="SpO₂ (%)",
            line=dict(width=2, dash="dot", color="#3498db")
        ))

        alert_rows = df[df["meta.alert"] == True]
        for _, row in alert_rows.iterrows():
            fig.add_vline(
                x=row["meta.event_date"],
                line_color="red",
                line_dash="dash",
                line_width=2
            )

        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Value",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Chart Error: {str(e)}")