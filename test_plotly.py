import streamlit as st
import pandas as pd
import plotly.graph_objects as go

data = pd.DataFrame({
    'Date': pd.date_range(start='1/1/2023', periods=5),
    'Queries': [10, 20, 15, 30, 25],
    'Likes': [5, 10, 8, 15, 12],
    'Dislikes': [2, 4, 3, 6, 5]
})

fig = go.Figure()

fig.add_trace(go.Bar(
    x=data['Date'],
    y=data['Queries'],
    name='Queries'
))

fig.add_trace(go.Scatter(
    x=data['Date'],
    y=data['Likes'],
    mode='markers',
    name='Likes',
    marker=dict(size=12, color='green')
))

fig.add_trace(go.Scatter(
    x=data['Date'],
    y=data['Dislikes'],
    mode='markers',
    name='Dislikes',
    marker=dict(size=12, color='red')
))

event = st.plotly_chart(fig, on_select="rerun")
st.write(event)
