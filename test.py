import unittest
import main
import exchange
from typing import List


class CEXStub(exchange.CEXExchange):
    def __init__(self, price_list: List[float]):
        self.price_list = price_list
        self.current_index = 0

    def getLatestBid(self, pair: str) -> float:
        self.current_index += 1
        return self.price_list[self.current_index - 1]


class RatchetTest(unittest.TestCase):
    def test_amount_gt_balance(self):
        main.sellPair("BTC/USD", 200, 20, 10)

    def test_extremum_finder(self):
        price_list = [178, 179, 180.2, 140.5, 150, 181, 140, 198, 100]
        main.cex = CEXStub(price_list)
        for i in range(len(price_list)):
            main.sellPair("BTC/USD", 50, 12, 10)
            if (i == 4):
                self.assertEqual(main.max_bid, 180.2)
                self.assertFalse(main.sell_start)
        self.assertTrue(main.sell_start)
        self.assertEqual(main.max_bid, 181)