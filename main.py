import warnings
from urllib.error import URLError

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scrapper import post_processing, scrap_pages, generate_summary

warnings.filterwarnings("ignore")


def local_test():
    scrap_pages(max_search=4, max_price=4000, min_area=40, days_since_created=2)
    post_processing()
    generate_summary()


def get_data(max_price=4000, min_area=40, days_since_created=2):
    df = scrap_pages(max_search=4, max_price=max_price, min_area=min_area, days_since_created=days_since_created, return_df=True, save=False)
    df = post_processing(df, save=False)
    return df


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
        customdata=np.stack((df['index'], df['price'], df['area'], df['rooms'], df['distance'].round(1), df['duration'].round()), axis=-1),
        hoverinfo='text',
        hovertemplate="<b>%{customdata[0]}</b><br>"
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


def main():
    try:
        max_price = st.sidebar.slider("Max Price", 0, 1000, 4000, 100)
        min_area = st.sidebar.slider("Min Area", 0, 100, 40, 1)
        days_since_created = st.sidebar.slider("Days Since Created", 1, 14, 2, 1)
        if st.button('Run Scrapper'):
            with st.spinner("Loading The Data"):
                df = get_data(max_price=max_price, min_area=min_area, days_since_created=days_since_created)
                if df.empty:
                    st.error("Empty Data Frame")
                else:
                    st.write(f"### Loaded {df.shape[0]} listings")
                    st.plotly_chart(make_map(df), use_container_width=True)
                    st.write(generate_summary(df, save=False))
                    st.write(df)

    except URLError as e:
        st.error(
            """
            **This demo requires internet access.**
            Connection error: %s
        """
            % e.reason
        )


def test_map():
    df = pd.read_csv('data/processed/processed_data_2022_07_02__21_16_17.csv', index_col=0)
    df[['lon', 'lat']] = df[['lon', 'lat']].astype(float)
    df = df.reset_index()
    fig = px.scatter_mapbox(
        df, lat="lat", lon="lon",
        # color="price", size="area",
        hover_data=['price', 'area'],
        hover_name='index',
        # range_color=[3000, 4000],
        # color_continuous_scale=px.colors.sequential.Bluered,
        size_max=20, zoom=12
    )
    fig.update_layout(mapbox_style='open-street-map', margin=dict(l=0, t=0, r=0, b=0, pad=0))
    fig.show()


if __name__ == "__main__":
    # local_test()
    # print(generate_summary())
    main()
    # test_map()
