from exchange import CEXExchange, ServerError, RemoteExecutionError
from typing import Optional, NamedTuple, Tuple
from cex_objects import CEXTicker, OrderStatus
import logging


class SellingDone(Exception):
    def __init__(self):
        super().__init__("Selling done")


class ChangeLevels(NamedTuple):
    ask_change: float
    bid_change: float


class TradingDirective(NamedTuple):
    action: str
    amount: float
    price: float
    pair :str


class Seller:
    def __init__(self, exchange: CEXExchange, action: str, pair: str, amount: float, threshold_percent: float, order_ttl: int = 10):
        self.exchange = exchange
        self.pair = pair
        self.src_curr = pair.split("/")[0]
        self.dst_curr = pair.split("/")[1]
        self.amount = amount
        self.threshold_percent = threshold_percent
        self.max_bid: float = -1
        self.current_order: Optional[str] = None
        self.max_order_ttl = order_ttl
        self.goal_balance: Optional[float] = None
        self.sell_started: bool = False
        self.order_ttl: int = 0
        self.action = action
        self.logger = logging.getLogger("4Trader")

    def define_goal_balance(self) -> None:
        current_balance = self.exchange.getBalance(self.src_curr)
        if self.goal_balance is None:
            self.goal_balance = current_balance - self.sell_amount
            if self.goal_balance < 0:
                self.goal_balance = 0  # продаем все
                self.sell_amount = current_balance
        else:
            self.sell_amount = current_balance - self.goal_balance  # если заново выполняем продажу, то допродаем разницу от изначальной цели
            if self.sell_amount < 0:
                raise Exception("Error in selling algorithm!")

    @property
    def goal_reached(self) -> bool:
        current_balance = self.exchange.getBalance(self.src_curr)
        return current_balance <= self.goal_balance

    @property
    def order_expired(self) -> bool:
        return self.order_ttl > self.max_order_ttl

    def control_order(self) -> None:
        if self.current_order is None:
            self.define_goal_balance()
            if self.sell_amount == 0:
                raise SellingDoneException()
            latest_bid = self.exchange.getLatestBid(self.pair)
            self.current_order = self.exchange.placeOrder(latest_bid, self.pair, self.sell_amount)
        else:
            order_status = self.exchange.getOrderStatus(self.current_order)
            if order_status == "active":
                self.order_ttl += 1
                if self.order_ttl > self.max_order_ttl:
                    self.exchange.cancelOrder(self.current_order)  # check status in the next iteration
            else:
                self.order_ttl = 0
                self.current_order = None

    def process_bid(self) -> None:
        latest_bid = self.exchange.getLatestBid(self.pair)
        if latest_bid > self.max_bid:
            self.max_bid = latest_bid
        elif ((1 - latest_bid / self.max_bid) * 100) >= self.threshold_percent:
            self.sell_started = True

    def process_ticker(self, ticker: CEXTicker) -> ChangeLevels:
        self.max_bid = max(self.max_bid, ticker.bid)
        self.max_ask = max(self.max_ask, ticker.ask)
        changes = ChangeLevels(ask_change=ticker.ask/self.max_ask, bid_change=ticker.bid/self.max_bid)
        return changes

    def process_changes(self, changes: ChangeLevels, ticker: CEXTicker) -> TradingDirective:
        amount_to_trade = -1
        price = -1
        action = self.action
        pair = self.pair
        if self.action == "buy":
            self.logger.debug(f"Asset's sell price changed by {changes.ask_change}%")
            if (changes.ask_change > 1) and ((changes.ask_change - 1) > self.threshold_percent):
                self.logger.debug(f"Threshold of {self.threshold_percent}% reached. Start buying...")
                amount_to_trade = self.amount
                price = ticker.ask
        else:
            self.logger.debug(f"Asset's buy price changed by {changes.bid_change}%")
            if (changes.bid_change < 1) and ((1 - changes.bid_change) > self.threshold_percent):
                self.logger.debug(f"Threshold of {self.threshold_percent}% reached. Start selling...")
                amount_to_trade = self.amount
                price = ticker.bid
        return TradingDirective(action, amount_to_trade, price, pair)

    def trade_asset(self, trading_directive: TradingDirective):
        if not self.current_order:
            self.current_order = self.exchange.place_order(trading_directive.action, trading_directive.pair,
                                                           trading_directive.price, trading_directive.amount).id
        else:
            order_info = self.exchange.get_order_info(self.current_order)
            order_status = order_info.status
            if order_status == OrderStatus.ACTIVE:
                self.order_ttl += 1
                if self.order_ttl <= self.max_order_ttl:
                    return
                self.exchange.cancel_order(self.current_order)
                remains = self.exchange.get_order_info(self.current_order).remains
                amount = self.amount - remains
                self.current_order = self.exchange.place_order(self.action, self.pair, price, amount).id
                self.order_ttl = 0
            elif order_status == OrderStatus.DONE:
                raise SellingDone()
            else:
                remains = self.exchange.get_order_info(self.current_order).remains
                amount = self.amount - remains
                self.current_order = self.exchange.place_order(self.action, self.pair, price, amount).id
                self.order_ttl = 0

    def process(self) -> None:
        ticker = self.exchange.get_ticker(self.pair)
        changes = self.process_ticker(ticker)
        trading_directive = self.process_changes(changes, ticker)
        if trading_directive.amount != -1 and trading_directive.price != -1:

        self.trade_asset(trading_directive)

