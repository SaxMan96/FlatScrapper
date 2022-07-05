import warnings
from urllib.error import URLError

import streamlit as st

from scrapper import post_processing, scrap_pages, generate_summary
from utils import make_map

warnings.filterwarnings("ignore")


def local_test():
    scrap_pages(max_search=4, max_price=4000, min_area=40, days_since_created=2)
    post_processing()
    generate_summary()


def get_data(max_search=3, max_price=4000, min_area=40, days_since_created=2, **kwargs):
    df = scrap_pages(max_search=max_search, max_price=max_price, min_area=min_area, days_since_created=days_since_created, return_df=True, save=False)
    df = post_processing(df, save=False, **kwargs)
    return df


def main():
    try:
        max_price = st.sidebar.slider("Max Price", 0, 1000, 4000, 100)
        min_area = st.sidebar.slider("Min Area", 0, 100, 40, 1)
        days_since_created = st.sidebar.slider("Days Since Created", 1, 14, 2, 1)
        max_search = st.sidebar.slider("Max Listings Search", 1, 1000, 300, 1)
        max_distance = st.sidebar.slider("Max Distance", 0.0, 10.0, 4.0, 0.1)
        max_duration = st.sidebar.slider("Max Duration", 0, 30, 10, 1)
        if st.button('Run Scrapper'):
            with st.spinner("Loading The Data"):
                df = get_data(
                    max_search=max_search,
                    max_price=max_price,
                    min_area=min_area,
                    days_since_created=days_since_created,
                    max_distance=max_distance,
                    max_duration=max_duration,
                )
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


if __name__ == "__main__":
    main()
