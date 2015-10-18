# coding: utf-8
import time
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import Column
import sqlalchemy.types as dbt
from sqlalchemy.orm.exc import NoResultFound

from cheapflight.models.base import EntityModel


class LowestPriceHistory(EntityModel):
    '''
    xx(a)n(n)(n)(n)(a)
        https://en.wikipedia.org/wiki/Airline_codes
    aaa
        https://en.wikipedia.org/wiki/International_Air_Transport_Association_airport_code
    '''

    __tablename__ = 'lowest_price_history'
    flight_date = Column(dbt.DATE, nullable=False)
    origin = Column(dbt.CHAR(3), nullable=False)
    destination = Column(dbt.CHAR(3), nullable=False)

    flight_no = Column(dbt.CHAR(8), nullable=False)
    price_cny = Column(dbt.DECIMAL(8, 2), nullable=False)
    first_seen_at = Column(sa.BigInteger, nullable=False)
    last_seen_at = Column(sa.BigInteger, nullable=False)

    @classmethod
    def add(cls, flight_date, origin, destination, flight_no, price_cny,
            first_seen_at=time.time()):

        payload = {
            'flight_date': flight_date,
            'origin': origin,
            'destination': destination,
            'flight_no': flight_no,
            'price_cny': price_cny,
            'first_seen_at': first_seen_at,
            'last_seen_at': first_seen_at,
        }
        return super(LowestPriceHistory, cls).add(**payload)

    @classmethod
    def get_latest_price(cls, flight_date, origin, destination):
        return cls.query.filter_by(
            flight_date=flight_date,
            origin=origin,
            destination=destination,
        ).order_by(
            sa.desc(cls.last_seen_at)
        ).limit(1)

    @classmethod
    def update_price(cls, flight_date, origin, destination, price, flight_no):
        if not isinstance(price, Decimal):
            raise ValueError("price should be of type decimal.Decimal")

        existed = cls.get_latest(flight_date, origin, destination)
        if existed is None or existed.price != price:
            return cls.add(flight_date, origin, destination)

        payload = {
            'last_seen_at': time.time()
        }
        if existed.flight_no != flight_no:
            payload['flight_no'] = flight_no

        existed.update(**payload)
        return existed.id