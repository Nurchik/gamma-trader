TICKER_RESPONSE = '{"timestamp":"1555429655","low":"77.01","high":"82.97","last":"80.55","volume":"962.53899874","volume30d":"22671.47783080","bid":80.03,"ask":81.47,"priceChange":"-2.38","priceChangePercentage":"-2.87","pair":"LTC:USD"}'
PLACE_ORDER_RESPONSE = '{"complete":true,"id":"8649363416","time":1555427005911,"pending":"100.0000000","amount":"100.0000000","type":"buy","price":"0.11"}'
PLACE_ORDER_ERROR = '{"error": "Error: Place order error: Insufficient funds."}'
GET_ORDER_DONE_RESPONSE = '{"id":"8544344631","type":"sell","time":1554220564111,"lastTxTime":"2019-04-02T20:16:16.691Z","lastTx":"8545703401","pos":null,"user":"up120757206","status":"d","symbol1":"BTC","symbol2":"USD","amount":"1.53693924","price":"220","fa:USD":"0.19","ta:USD":"118.12","remains":"0.00000000","a:BCH:cds":"0.53693924","a:USD:cds":"118.12","f:USD:cds":"0.19","tradingFeeMaker":"0.16","tradingFeeTaker":"0.25","tradingFeeStrategy":"userVolumeAmount","tradingFeeUserVolumeAmount":"0","orderId":"8544344631"}'
GET_ORDER_CANCELLED_RESPONSE = '{"id":"8649363416","type":"buy","time":1555427005911,"lastTxTime":"2019-04-16T15:04:51.633Z","lastTx":"8649369119","pos":null,"user":"up120757206","status":"c","symbol1":"XLM","symbol2":"USD","amount":"100.00000000","kind":"api","price":"0.11","remains":"100.0000000","a:USD:cds":"11.03","tradingFeeMaker":"0.16","tradingFeeTaker":"0.25","tradingFeeStrategy":"userVolumeAmount","tradingFeeUserVolumeAmount":"4467301","orderId":"8649363416"}'
GET_ORDER_NOT_FOUND = 'null'
CANCEL_ORDER_RESPONSE = 'true'
CANCEL_ORDER_NOT_FOUND = '{"error": "Error: Order not found"}'
GENERAL_ERROR = '{"error":"Got error when processing request. Try again later."}'