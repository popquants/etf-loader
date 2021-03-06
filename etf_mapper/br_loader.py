import csv
import datetime as dt
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from loguru import logger


class ISharesLoader(object):
    """
    A supporting class to manage and sort all data related to retrieving details on ETF as issued by iShares.

    """

    def __init__(self):
        self.logger = logger

    @staticmethod
    def load_iso_mapping() -> pd.DataFrame:
        """
        Loads and returns the stored ISO 3166-1 mapping for each country. This includes both the alpha-2 and alpha-3
        values.

        Returns:
            pd.DataFrame: The frame including the ISO mappings.

        """

        file_path = Path('data') / 'iso_country_mapping.csv'
        iso_frame = pd.read_csv(file_path)
        iso_frame['Alpha-2 code'] = iso_frame['Alpha-2 code'].apply(lambda x: x.replace(' ', '')).copy()
        iso_frame['Alpha-3 code'] = iso_frame['Alpha-3 code'].apply(lambda x: x.replace(' ', '')).copy()

        return iso_frame

    @staticmethod
    def load_ishares_products(country: str = 'us') -> pd.DataFrame:
        """
        Loads the previously stored overview of all iShares ETFs.

        Args:
            country (str, optional): Defines the country to scan for. Currently only 'us' is supported.

        Returns:
            pd.DataFrame: The stored ETF information.

        """

        file_path = Path('data') / f'product_screener_{country}.csv'
        us_products_frame = pd.read_csv(file_path)

        return us_products_frame

    @logger.catch()
    def download_compositions_of_country(self, country: str) -> None:
        """
        Routine to download all previously specified ETFs compositions from BlackRock. and export them via csv files.

        Args:
            country: The country code for the specified set of ETF compositions to download.

        """

        us_frame = self.load_ishares_products(country)
        download_date = dt.date.today()
        for product_nr, product_info in us_frame.iterrows():
            ticker = product_info['Ticker']
            url = product_info['URL']
            self.logger.info(f'Downloading compo for {ticker} from {url}!')
            composition_link = self.get_composition_download_link(url)
            if composition_link:
                try:
                    composition = self.download_composition(composition_link)
                    export_path = Path('downloads') / 'compositions' / f'{download_date}'
                    if not export_path.exists():
                        export_path.mkdir(parents=True)

                    composition_file_name = f'{ticker}_holdings_{download_date}.csv'
                    composition.to_csv(export_path / composition_file_name)
                except ValueError:
                    warning_msg = f'Invalid downloaded file for {ticker} from {url}, no data downloaded!'
                    self.logger.warning(warning_msg)
            else:
                warning_msg = f'No composition found for {ticker} at {url}!'
                self.logger.warning(warning_msg)

    @staticmethod
    def download_composition(download_link: str) -> pd.DataFrame:
        """
        Downloads the composition of an ETF as per the specified download link.

        Args:
            download_link (str): The source link for the composition.

        Returns:
            pd.DataFrame: The ETF composition

        """

        with requests.Session() as s:
            download = s.get(download_link)

            decoded_content = download.content.decode('utf-8')
            cr = csv.reader(decoded_content.splitlines(), delimiter=',')
            my_list = list(cr)

        composition = pd.DataFrame(my_list[10:-1], columns=my_list[9])

        return composition

    def get_composition_download_link(self, etf_url: str):
        """
        Gets the download link for the ETF composition based on the general ETF page link.

        Args:
            etf_url (str): The ETF page link.

        Returns:
            str: The link for the ETF composition

        """

        response = requests.get(etf_url)
        single_etf_soup = BeautifulSoup(response.content, 'html.parser')
        actual_link = None

        for link in single_etf_soup.find_all('a'):
            try:
                current_link = link.get('href')
                if 'csv' in current_link:
                    actual_link = current_link
                    break
            except Exception as e:
                self.logger.warning(e)

        download_link = f"https://www.ishares.com{actual_link}" if actual_link else None

        return download_link
