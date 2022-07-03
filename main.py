import warnings
from urllib.error import URLError

import pandas as pd
import plotly.express as px
import streamlit as st

from scrapper import post_processing, scrap_pages, generate_summary


def main():
    scrap_pages(max_search=1000, max_price=4000, min_area=40, days_since_created=2)
    post_processing()
    generate_summary()


def get_data(max_price=4000, min_area=40, days_since_created=2):
    df = scrap_pages(max_search=1000, max_price=max_price, min_area=min_area, days_since_created=days_since_created, return_df=True)
    df = post_processing(df)
    return df


def make_map(df):
    df[['lon', 'lat']] = df[['lon', 'lat']].astype(float)
    df = df.reset_index()
    fig = px.scatter_mapbox(
        df, lat="lat", lon="lon", color="price", size="area",
        hover_data=['price', 'area'], hover_name='index', range_color=[3000, 4000],
        color_continuous_scale=px.colors.sequential.Bluered, size_max=10, zoom=12
    )
    fig.update_layout(mapbox_style='open-street-map')
    return fig


def streamlit_main():
    warnings.filterwarnings("ignore")
    try:
        max_price = st.sidebar.slider("Max Price", 0, 1000, 4000, 100)
        min_area = st.sidebar.slider("Min Area", 0, 100, 40, 1)
        days_since_created = st.sidebar.slider("Days Since Created", 1, 14, 1, 1)
        if st.button('Run Scrapper'):
            with st.spinner("Loading The Data"):
                df = get_data(max_price=max_price, min_area=min_area, days_since_created=days_since_created)
                st.balloons()
                summary = generate_summary(df)
                if df.empty:
                    st.error("Empty Data Frame")
                else:
                    st.write(f"### Loaded {df.shape[0]} listings")
                    fig = make_map(df)
                    st.plotly_chart(fig, use_container_width=True)
                    st.write(summary)
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
        df, lat="lat", lon="lon", color="price", size="area",
        hover_data=['price', 'area'],
        hover_name='index',
        color_continuous_scale=px.colors.sequential.Bluered,
        range_color=[3000, 4000], size_max=10, zoom=13
    )
    fig.update_layout(mapbox_style='open-street-map')
    fig.show()


if __name__ == "__main__":
    # main()
    streamlit_main()
    # test_map()
