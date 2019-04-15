import argparse
from exchange import CEXExchange
from trader import Trader, OrderDone, OrderExpired
import time
import logging.config
import yaml


parser = argparse.ArgumentParser()
parser.add_argument('--pair', type=str, required=True)
parser.add_argument('--amount', type=float, required=True)
parser.add_argument('--action', type=str, required=True)
parser.add_argument('--threshold_percent', type=float, required=True)
parser.add_argument('--order_ttl', type=int, default=10)
parser.add_argument('--significant_digits', type=int, default=3)
parser.add_argument('--processing_period', type=int, default=5)

args = vars(parser.parse_args())

CEX_API_SECRET = "Reio4qcibCAavaNa4G74HhlTE"
CEX_API_KEY = "wbgSkWtMDnCLkH1Pfep6gb8d4"
CEX_USERNAME = "up120757206"

cex = CEXExchange(CEX_USERNAME, CEX_API_KEY, CEX_API_SECRET)
seller = Trader(cex, args["action"], args["pair"], args["amount"], args["threshold_percent"],
                args["order_ttl"], args["significant_digits"])

with open("logging_config.yaml", "r") as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)

if __name__ == "__main__":
    logger = logging.getLogger("gamma")
    logger.info(f'Action "{args["action"]}" started. Amount: {args["amount"]}. Pair: {args["pair"]}.'
                f'Threshold: {args["threshold_percent"]}%. Order TTL: {args["order_ttl"]}.'
                f'Significant Digits: {args["significant_digits"]}. Processing Period: {args["processing_period"]}')
    while True:
        try:
            seller.process()
            time.sleep(args["processing_period"])
        except OrderDone:
            logger.info("Work is done!")
            break
        except OrderExpired:
            continue
        except Exception as exc:
            logger.exception("Unhandled exception!")
            break
