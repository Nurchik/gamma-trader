#!/bin/bash

counter=0

SELL_TP=1.5
BUY_TP=2.1
PAIR="BCH/USD"
AMOUNT=0.1

while true; do
    python main.py --pair "$PAIR" --amount ${AMOUNT} --action buy --threshold_percent ${BUY_TP}
    rc=$?
    if [[ ! rc -eq 0 ]]; then
        exit 1
    fi
    counter=$((counter+1))
    if [[ ${counter} > 2 ]]; then
        false
    else
        python main.py --pair "$PAIR" --amount ${AMOUNT} --action sell --threshold_percent ${SELL_TP}
    fi
    rc=$?
    if [[ ! rc -eq 0 ]]; then
        exit 1
    fi
done
