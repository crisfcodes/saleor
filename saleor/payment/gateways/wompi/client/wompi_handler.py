import json
from typing import Dict

import requests

from .constants import HTTP_STATUS_CODE, WompiURL
from .exceptions import WompiException, WompiTransactionException
from .objects import AcceptanceTokenDAO, TransactionDAO


class MethodType:
    GET = "GET"
    POST = "POST"


class TransactionStates:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    VOIDED = "VOIDED"
    ERROR = "ERROR"


class WOMPI_PAYMENT_METHODS:
    CARD = "CARD"
    NEQUI = "CARD"
    PSE = "CARD"
    CASH_AT_BBC = "CARD"
    BANC_TRA_Button = "BANC_TRA_Button"


class WompiHandler:
    method_type = None
    authentication_required = False
    url = ""
    payload = ""
    exception_class = WompiException

    def __init__(self, config):
        self._key = config.get("key")
        self._secret = config.get("secret")
        self.sandbox = config.get("sandbox", True)
        self.authentication_required = True
        assert self._key != None, "Invalid key for Wompi"
        assert self._secret != None, "Invalid Secret for Wompi"

    @property
    def _get_host(self):
        return WompiURL.SANDBOX_URL if self.sandbox else WompiURL.PRODUCTION_URL

    def _make_url(self, method_name):
        return "{}/{}".format(self._get_host, method_name)

    @property
    def _get_url(self):
        return self.url

    def _append_authorization(self, headers):
        if self.authentication_required:
            headers["Authorization"] = "Bearer {}".format(self._secret)
        return headers

    def send_request(self):
        headers = {"Content-Type": "application/json"}
        headers = self._append_authorization(headers)
        response = requests.request(
            self.method_type, self._get_url, headers=headers, data=self.payload
        )
        if response.status_code in HTTP_STATUS_CODE.OK_CODES:
            return response.json()
        else:
            raise self.exception_class(response.text)

    def void_transaction(self, **kwargs):
        pass

    def refund(self, **kwargs):
        pass

    def process_payment(self, **kwargs):
        pass


class AcceptanceToken(WompiHandler):
    path = "merchants/{key}"
    method_type = MethodType.GET
    authentication_required = False
    DAO = AcceptanceTokenDAO

    @property
    def _get_url(self):
        return self._make_url(self.path.format(key=self._key))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def send_request(self):
        resp = super().send_request()
        return self.DAO(**resp.get("data"))


class Transaction(WompiHandler):
    path = "transactions"
    method_type = MethodType.POST
    authentication_required = True
    DAO = TransactionDAO
    exception_class = WompiTransactionException

    @property
    def _get_url(self):
        return self._make_url(self.path)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_transaction(self, payload: Dict):
        # TODO: moce to validate function.
        required_keys = [
            "acceptance_token",
            "amount_in_cents",
            "customer_email",
            "reference",
            "payment_method",
        ]
        if not set(required_keys).issubset(set(payload.keys())):
            raise self.exception_class("Required keys are not provided ")
        self.payload = json.dumps(payload)
        return self.send_request()

    def send_request(self):
        resp = super().send_request()
        return self.DAO(**resp.get("data"))
