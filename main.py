import argparse
from exchange import CEXExchange
import time

parser = argparse.ArgumentParser()
parser.add_argument('--pair', type=str, required=True)
parser.add_argument('--amount', type=float, required=True)
parser.add_argument('--threshold_percent', type=float, required=True)
parser.add_argument('--order_ttl', type=int, default=10)

args = vars(parser.parse_args())

CEX_API_SECRET = "Reio4qcibCAavaNa4G74HhlTE"
CEX_API_KEY = "wbgSkWtMDnCLkH1Pfep6gb8d4"
CEX_USERNAME = "up120757206"

cex = CEXExchange(CEX_USERNAME, CEX_API_KEY, CEX_API_SECRET)

max_bid = 0
current_order = None
order_ttl = 0
goal_balance = None
sell_start = False


def controlOrder(pair, amount, max_order_ttl):
    global max_bid, current_order, order_ttl, goal_balance, sell_start
    if current_order is None:
        src_coin = pair.split("/")[0]
        current_balance = cex.getBalance(src_coin)
        if current_balance <= goal_balance:
            return True
        goal_balance = current_balance - amount
        if goal_balance < 0:
            goal_balance = 0
            amount = current_balance
        latest_bid = cex.getLatestBid(pair)
        current_order = cex.placeOrder(latest_bid, pair, amount)
    else:
        order_status = cex.getOrderStatus(current_order)
        if order_status == "active":
            order_ttl += 1
        elif order_status == "done":
            return True
        else:
            current_order = None  # done with work
            order_ttl = 0

        if order_ttl >= max_order_ttl:
            result = cex.cancelOrder(current_order)
            if result:
                current_order = None
                order_ttl = 0


def sellPair(pair, amount, threshold_percent, max_order_ttl):
    global max_bid, current_order, order_ttl, goal_balance, sell_start
    if not sell_start:
        last_bid = cex.getLatestBid(pair)
        if last_bid > max_bid:
            max_bid = last_bid
        elif ((1 - last_bid/max_bid) * 100) >= threshold_percent:
            sell_start = True
    else:
        controlOrder(pair, amount, max_order_ttl)
    return False


if __name__ == "__main__":
    global current_order
    try:
        while True:
            res = sellPair(args["pair"], args["amount"], args["threshold_percent"], args["order_ttl"])
            if res:
                break
            time.sleep(3)
        print("work's done")
    except KeyboardInterrupt:
        print('interrupted!')
        if current_order:
            cex.cancelOrder(current_order)
        print("done")