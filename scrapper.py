import datetime
import glob
import json
import logging
import math
import unicodedata
import urllib.parse
from datetime import datetime
from urllib import request
from urllib.error import HTTPError

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
LISTINGS_ON_PAGE_LIMIT = 72
MIN_DISTANCE = 4
MIN_DURATION = 7
MIN_AREA = 50
MAX_PRICE = 4200
CENTER_LAT = '52.2304944'
CENTER_LON = '21.010445040894194'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36',
    'Cookie': 'some cookie data'
}

import textwrap


def generate_summary(df=None, save=True):
    if df is None:
        data_path = sorted(glob.glob("data/processed/*.csv"))[-1]
        logging.info(f"data path: {data_path}")
        df = pd.read_csv(data_path, index_col=0)
    df = df.head(15)
    current_date = datetime.now().strftime("%Y_%m_%d")
    summary = []
    for i, row in df.iterrows():
        row = df.loc[i]
        if np.isnan(row.distance):
            distance = "???"
            duration = "???"
        else:
            distance = round(row.distance, 1)
            duration = round(row.duration)
        if abs(row.Czynsz) == 1:
            czynsz = "plus czynsz ??? zł"
            price = row.price
        else:
            czynsz = f"w tym czynsz {row.Czynsz}zł"
            price = row.price + row.Czynsz

        summary.append((f"""
- [{i}] {row.localization_info.replace("Warszawa, ", "")} ({distance}km, {duration}min do centrum) [link]({row.listing_url})
    - {price}zł ({czynsz}) | {row.rooms} pokoje
    - {int(row.area)} m2 | piętro {row.Piętro} {row['Rodzaj zabudowy']} 
        """))
    summary = "\n".join(summary)
    if save:
        text_file = open(f"summary/message_{current_date}.md", "w")
        text_file.write(summary)
        text_file.close()
    return summary


def _get_lat_lon(address):
    url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) + '?format=json'
    response = requests.get(url).json()
    if not response:
        print(address)
        return None, None
    return response[0]["lat"], response[0]["lon"]


def _get_dist_time_cen(lat, lon):
    if lat is None or lon is None:
        return None, None
    r = requests.get(f"http://router.project-osrm.org/route/v1/car/{lon},{lat};{CENTER_LON},{CENTER_LAT}?overview=false""")
    route_1 = json.loads(r.content)["routes"][0]
    return route_1["distance"] / 1000, route_1["duration"] / 60


def _get_price_threshold(x):
    return 2300 - 1.9 * (1 - np.exp(0.095 * x))


def post_processing(df=None, save=True):
    if df is None:
        data_path = sorted(glob.glob("data/raw/*.csv"))[-1]
        logging.info(f"data path: {data_path}")
        df = pd.read_csv(data_path, index_col=0)
        logging.info(f"data shape {df.shape}")
    df.price = df.price.str.replace('zł/mc', '').str.replace(',', '.').astype(float)
    df.Kaucja = df.Kaucja.str.replace('zapytaj', '-1').str.replace('zł', '').str.replace(' ', '').str.strip().fillna(0).str.replace(',', '.').astype(float)

    df.rooms = df.rooms.apply(lambda x: [int(d) for d in x if d.isdigit()][0])
    df.area = df.area.str.replace('m2', '').str.strip().astype(float)

    localization_df = df.localization_info.str.split(',', expand=True)
    if localization_df.shape[1] == 4:
        df[['city', 'district_l1', 'district_l2', 'street']] = localization_df
        df.street = df.street.fillna(df.district_l2)
    elif localization_df.shape[1] == 3:
        df[['city', 'district_l1', 'street']] = localization_df
        df['district_l2'] = None

    df.drop(['Powierzchnia', 'Obsługa zdalna', 'Stan wykończenia'], axis=1, inplace=True)
    df.Czynsz = df.Czynsz.str.replace('zapytaj', '-1').str.replace('zł/miesiąc', '').str.replace(' ', '').str.replace(',', '.').astype(float)

    df.city = df.city.str.strip()
    df.district_l1 = df.district_l1.str.strip()
    df.district_l2 = df.district_l2.str.strip()
    df.street = df.street.str.strip().fillna('')
    df.localization_info.replace(',', '')

    df = _drop_fakes(df)
    df = _download_geo_data(df)
    df = _filter_data(df)
    df = _order_by_rank(df)

    current_time = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
    if save:
        df.to_csv(f'data/processed/processed_data_{current_time}.csv')
    return df


def _drop_fakes(df):
    df['_czynsz'] = df.Czynsz.replace(-1, 0)
    df['_price'] = df.price + df._czynsz
    df['fake'] = _get_price_threshold(df.area) > df.price
    df = df[~df.fake]
    return df


def _order_by_rank(df):
    df['_area_rank'] = df.area.rank(method='max', ascending=False)
    df['_price_rank'] = df.price.rank(method='max')
    df['_distance_rank'] = df.distance.rank(method='max')
    df['_duration_rank'] = df.duration.rank(method='max')
    df['_rank'] = df[['_area_rank', '_price_rank', '_distance_rank', '_duration_rank']].sum(axis=1)
    df = df.sort_values('_rank').reset_index(drop=True)
    return df


def _download_geo_data(df):
    logging.info("Downloading Geo Info")
    for i, row in tqdm(df.iterrows(), total=len(df)):
        row = df.loc[i]
        address = " ".join([row.city, row.district_l1, row.street]).replace('ul. ', '').replace('os. ', '').replace('/', '')
        lat, lon = _get_lat_lon(address)
        distance, duration = _get_dist_time_cen(lat, lon)
        df.at[i, 'lat'] = lat
        df.at[i, 'lon'] = lon
        df.at[i, 'distance'] = distance
        df.at[i, 'duration'] = duration
    return df


def _filter_data(df):
    return df[
        (df.distance <= MIN_DISTANCE) &
        (df.duration < MIN_DURATION) &
        (df.area >= MIN_AREA) &
        (df['_price'] <= MAX_PRICE)
        ]


def _scrap_listing(listing_element):
    listing_url = f"https://www.otodom.pl{listing_element.find_all('a', href=True)[0]['href']}"
    listing_property_dict = {'listing_url': listing_url}
    request_info = request.Request(listing_url)
    try:
        requested_html = request.urlopen(request_info)
    except HTTPError as e:
        print(f"Skipping: {e.code}")
        return {}
    soup = BeautifulSoup(requested_html, features='html.parser')
    property_list = soup.find_all('div', {'class': 'css-1ccovha estckra9'})
    for property_element in property_list:
        property_elem_list = property_element.find_all('div', {'class': 'css-1qzszy5 estckra8'})
        key = property_elem_list[0].text
        value = property_elem_list[1].text
        listing_property_dict[key] = value

    return listing_property_dict


def scrap_pages(max_search, days_since_created=1, min_area=35, max_price=4500, return_df=False, save=True):
    pages_to_scrap = math.ceil(max_search / LISTINGS_ON_PAGE_LIMIT)
    current_time = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
    result_list = []
    for current_page in range(1, pages_to_scrap + 1):
        logging.info(f'Page {current_page}/{pages_to_scrap}')
        url = textwrap.dedent(f"""
        https://www.otodom.pl/pl/oferty/wynajem/mieszkanie/
        wiele-lokalizacji?distanceRadius=0
        &page={current_page}
        &limit={LISTINGS_ON_PAGE_LIMIT}
        &market=ALL
        &ownerTypeSingleSelect=ALL
        &priceMax={max_price}
        &areaMin={min_area}
        &roomsNumber=%5BTWO%2CTHREE%5D
        &locations=%5Bdistricts_6-3319%2Cdistricts_6-39%2Cdistricts_6-40%2Cdistricts_6-44%2Cdistricts_6-53%2Cdistricts_6-117%5D
        &daysSinceCreated={days_since_created}
        &media=%5B%5D
        &extras=%5B%5D
        &viewType=listing
        """).replace('\n', '')

        request_info = request.Request(url, headers=HEADERS)

        try:
            requested_html = request.urlopen(request_info)
        except HTTPError as e:
            print(f"Skipping: {e.code}")
            continue

        soup = BeautifulSoup(requested_html, features='html.parser')
        _listings_div = soup.find_all('div', {'data-cy': "search.listing"})
        if len(_listings_div) < 2:
            break
        listings_div = _listings_div[1]
        listings_list = listings_div.find_all('li', {"class": "css-p74l73 es62z2j17"})

        for listing_element in tqdm(listings_list):
            listing_property_dict = {}
            header_basic_info = [
                unicodedata.normalize("NFKD", e.text) for e in
                listing_element.find_all('span', {'class': 'css-rmqm02 eclomwz0'})]
            listing_property_dict['price'] = header_basic_info[0]
            listing_property_dict['rooms'] = header_basic_info[1]
            listing_property_dict['area'] = header_basic_info[2] if len(header_basic_info) > 2 else None
            listing_property_dict['localization_info'] = \
                listing_element.find_all('span', {'class': 'css-17o293g es62z2j9'})[0].text
            listing_property_dict = {**listing_property_dict, **_scrap_listing(listing_element)}
            result_list.append(listing_property_dict)
        df = pd.DataFrame(result_list).drop_duplicates()
    if save:
        df.to_csv(f'data/raw/scrapped_raw_data_{current_time}.csv')
    if return_df:
        return df
