import numpy as np
import plotly.graph_objects as go
import streamlit as st


def make_map(df):
    df[['lon', 'lat']] = df[['lon', 'lat']].astype(float)
    df = df.reset_index()

    data = go.Scattermapbox(
        lat=list(df['lat']),
        lon=list(df['lon']),
        mode='markers+text',
        marker=dict(size=20, color='Black'),
        textposition='middle center',
        textfont={'family': "Times", 'size': 12, 'color': "White"},
        text=df['index'].astype(str),
        customdata=np.stack((
            df['index'], df['price'], df['area'], df['rooms'],
            df['distance'].round(1), df['duration'].round(), df['localization_info']),
            axis=-1),
        hoverinfo='text',
        hovertemplate="<b>%{customdata[0]} %{customdata[6]}</b><br>"
                      + "%{customdata[1]}zł | %{customdata[2]}m2 | %{customdata[3]} rooms<br>"
                      + "to centre: %{customdata[4]}km %{customdata[5]}min<br>"
    )

    fig = go.Figure(data=data)
    fig.update_layout(
        margin=dict(l=0, t=0, r=0, b=0, pad=0),
        mapbox=dict(
            accesstoken=st.secrets["MAPBOX_ACCESS_TOKEN"],
            center=dict(lat=52.23, lon=21.01),
            style='light',
            zoom=12,
        )
    )

    return fig
