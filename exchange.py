import requests
import logging
import hmac
import hashlib
import time
from typing import Dict, Any, Type, cast, Optional
from cex_objects import CEXApiResponse, CEXApiData, CEXTicker, CEXOrderInfo, CEXPlacedOrderInfo

BASE_URL = 'https://cex.io/api/%s/'

PUBLIC_COMMANDS = {
    'currency_limits',
    'ticker',
    'last_price',
    'last_prices',
    'convert',
    'price_stats',
    'order_book',
    'trade_history'
}


class ServerError(Exception):
    def __init__(self):
        super().__init__("CEX.io server error")


class RemoteExecutionError(Exception):
    def __init__(self, cause=''):
        super().__init__(f"API call error -> {cause}")
        self.cause = cause


class OrderNotFound(Exception):
    def __init__(self, order_id):
        super().__init__(f'Order {order_id} not found')
        self.order_id: str = order_id


class CEXExchange:
    def __init__(self, username: str, api_key: str, api_secret: str):
        self.api_key = api_key
        self.username = username
        self.api_secret = api_secret
        self.logger = logging.getLogger("gamma.CEXExchange")

    def __nonce(self) -> str:
        return str(int(time.time() * 1000))

    def __signature(self, nonce: str) -> str:
        message = nonce + self.username + self.api_key
        signature = hmac.new(bytearray(self.api_secret.encode('utf-8')), message.encode('utf-8'),
                             digestmod=hashlib.sha256).hexdigest().upper()
        return signature

    def api_call(self, data_type: Optional[Type[CEXApiData]], command: str, param: Dict[str, Any] = None, action='') -> CEXApiResponse:
        request_url = (BASE_URL % command) + action
        if param is None:
            param = {}

        self.logger.debug(f"request_url = {request_url}, params = {param}")

        if command not in PUBLIC_COMMANDS:
            nonce = self.__nonce()
            param.update({
                'key': self.api_key,
                'signature': self.__signature(nonce),
                'nonce': nonce
            })

        if len(param.keys()) > 0:
            method = 'post'
        else:
            method = 'get'

        result = self.request(request_url, method, param)
        self.logger.debug(f"Response from CEX. Status code: {result.status_code}. Body: {result.content}.")
        if result.status_code != 200:
            raise ServerError()
        response = CEXApiResponse(result.json(), data_type)
        # self.logger.debug(f"response = {response}")
        return response

    def request(self, url: str, method: str, param: Dict[str, Any]) -> requests.Response:
        if method == "get":
            result = requests.get(url, headers={'User-agent': 'bot-cex.io-' + self.username})
        else:
            result = requests.post(url, json=param, headers={'User-agent': 'bot-cex.io-' + self.username})
        return result

    def place_order(self, order_type: str, pair: str, price: float, amount: float) -> CEXPlacedOrderInfo:
        params = {
            'type': order_type,
            'amount': amount,
            'price': price
        }

        response = self.api_call(CEXPlacedOrderInfo, 'place_order', params, pair)
        if response.error or response.ok != "ok":
            raise RemoteExecutionError(response.error)
        return cast(CEXPlacedOrderInfo, response.data)

    def cancel_order(self, order_id: str) -> None:
        response = self.api_call(None, 'cancel_order', {'id': order_id})
        if not response.error:
            cancelled = response.json_obj
            if type(cancelled) != bool:
                raise Exception("Cannot cancel order!")
            if not cancelled:
                raise Exception("Cannot cancel order!")
        else:
            raise RemoteExecutionError(response.error)

    def get_order_info(self, order_id: str) -> CEXOrderInfo:
        response = self.api_call(CEXOrderInfo, 'get_order', {'id': order_id})
        if not response.data:
            raise OrderNotFound(order_id)
        if response.error or response.ok != "ok":
            raise RemoteExecutionError(response.error)
        return cast(CEXOrderInfo, response.data)

    def get_ticker(self, pair: str) -> CEXTicker:
        response = self.api_call(CEXTicker, "ticker", None, pair)
        if response.error or response.ok != "ok":
            raise RemoteExecutionError(response.error)
        return cast(CEXTicker, response.data)


