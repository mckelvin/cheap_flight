# coding: utf-8
import lxml
import lxml.cssselect
import html5lib
from decimal import Decimal
from datetime import date
import requests

from cheapflight.libs.mc import cache

from cheapflight.utils import exchange_to_cny, get_fake_ip


MC_KEY_WEB_RESULT = ("airasia:web_result:{dep_code}:{arr_code}:"
                     "{departure_date}:{return_date}")


class Searcher(object):

    BASE_URL = 'https://booking.airasia.com/Flight/Select'
    BASE_HTTP_HEADER = {
        'accept': ('text/html,application/xhtml+xml,application/xml;'
                   'q=0.9,image/webp,*/*;q=0.8'),
        'accept-encoding': 'gzip, deflate, sdch',
        'accept-language': 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4,ja;q=0.2',
        'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/45.0.2454.93 Safari/537.36'),
    }
    AIRLINE_NAME = 'AirAsia'

    def __init__(self):
        self.http = requests.Session()

    @cache(MC_KEY_WEB_RESULT, 60)
    def search(self, dep_code, arr_code, departure_date, return_date=None):
        return self.search_without_cache(dep_code, arr_code, departure_date,
                                         return_date)

    def search_without_cache(self, dep_code, arr_code, departure_date,
                             return_date=None):
        http_headers = self.BASE_HTTP_HEADER.copy()
        http_headers['x-forwarded-for'] = get_fake_ip()
        dd1_str = departure_date.strftime("%Y-%m-%d")
        params = {
            'o1': dep_code,
            'd1': arr_code,
            'dd1': dd1_str,
            'ADT': 1,
            'CHD': 0,
            'inl': 0,
            's': True,
            'mon': True,
            'loy': True,
            'cc': 'CNY',
        }
        if return_date is not None:
            params["dd2"] = return_date.strftime("%Y-%m-%d")

        res = self.http.get(
            self.BASE_URL,
            headers=http_headers,
            params=params
        )
        if res.status_code == 200:
            return res.text

        if res.status_code in (502, 504):
            return
        else:
            raise NotImplementedError(
                "Unknown code: %s\n%s" % (res.status_code, res.text)
            )

    @staticmethod
    def parse_lowest_price(html_data):
        htmlparser = html5lib.HTMLParser(
            tree=html5lib.treebuilders.getTreeBuilder("lxml"),
            namespaceHTMLElements=False
        )

        page = htmlparser.parse(html_data)

        table_selector = lxml.cssselect.CSSSelector("table.avail-table")
        fare_selector = lxml.cssselect.CSSSelector("div.avail-fare-price")
        total_price = Decimal(0)
        for table in table_selector(page):
            price_str_list = [
                fare.text.strip()
                for fare in fare_selector(table)
            ]

            if not price_str_list:
                raise ValueError(html_data)

            lowest_price = None
            currency_code = None
            for price_str in price_str_list:
                price_, currency_code_ = price_str.split(" ")
                if currency_code is None:
                    currency_code = currency_code_
                else:
                    assert currency_code == currency_code_
                price_ = Decimal(
                    price_.strip(u"≈ ").replace(",", "")
                )
                if lowest_price is None or price_ < lowest_price:
                    lowest_price = price_

            assert currency_code is not None

            if currency_code != 'CNY':
                lowest_price_in_cny = exchange_to_cny(currency_code, lowest_price)
            else:
                lowest_price_in_cny = lowest_price

            total_price += lowest_price_in_cny
        return total_price

    def get_lowest_price(self, dep_code='PEK', arr_code='KUL',
                         departure_date=date(2016, 5, 2), return_date=None):
        data = self.search(dep_code, arr_code, departure_date, return_date)
        return self.parse_lowest_price(data)


__all__ = ['Searcher']
