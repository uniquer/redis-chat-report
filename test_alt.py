import streamlit as st
import pandas as pd
import altair as alt

data = pd.DataFrame({
    'Date': pd.date_range(start='1/1/2023', periods=5),
    'Queries': [10, 20, 15, 30, 25],
    'Likes': [5, 10, 8, 15, 12],
    'Dislikes': [2, 4, 3, 6, 5]
})

selection = alt.selection_point(fields=['Date'], name='selector_date')
like_selection = alt.selection_point(fields=['Date'], name='selector_like')
dislike_selection = alt.selection_point(fields=['Date'], name='selector_dislike')

bars = alt.Chart(data).mark_bar().encode(
    x='Date:T',
    y='Queries:Q',
    opacity=alt.condition(selection, alt.value(1), alt.value(0.3))
).add_params(selection)

likes = alt.Chart(data).mark_point(color='green', filled=True, size=100).encode(
    x='Date:T',
    y='Likes:Q',
    opacity=alt.condition(like_selection, alt.value(1), alt.value(0.3))
).add_params(like_selection)

dislikes = alt.Chart(data).mark_point(color='red', filled=True, size=100).encode(
    x='Date:T',
    y='Dislikes:Q',
    opacity=alt.condition(dislike_selection, alt.value(1), alt.value(0.3))
).add_params(dislike_selection)

chart = alt.layer(bars, likes, dislikes)
event = st.altair_chart(chart, on_select="rerun")
st.write(event)
