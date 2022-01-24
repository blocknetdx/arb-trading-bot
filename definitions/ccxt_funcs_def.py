import json
import logging
import os
import time

import ccxt

import arbtaker_settings as settings
import definitions.logger as logger

ccxt_log = logger.setup_logger(name="CCXT_LOG", log_file='logs/ccxt.log', level=logging.INFO)


def init_ccxt_instance(exchange, hostname=None):
    # CCXT instance
    script_dir = os.path.dirname(__file__)
    api = None
    api_secret = None
    with open('utils/keys.local.json') as json_file:
        data_json = json.load(json_file)
        for data in data_json['api_info']:
            if exchange in data['exchange']:
                api = data['api']
                api_secret = data['secret']
    # if exchange in ccxt.exchanges:
    exchange_class = getattr(ccxt, exchange)
    print(exchange_class)
    if hostname:
        instance = exchange_class({
            'apiKey': api,
            'secret': api_secret,
            'enableRateLimit': True,
            'rateLimit': 1000,
            'hostname': hostname,  # 'global.bittrex.com',
        })
    else:
        instance = exchange_class({
            'apiKey': api,
            'secret': api_secret,
            'enableRateLimit': True,
            'rateLimit': 1000,
        })
    err_count = 0
    while True:
        try:
            instance.load_markets()
            print(instance)
        except Exception as e:
            err_count += 1
            ccxt_manage_error(e, err_count)
            time.sleep(err_count)
        else:
            break
    return instance


def ccxt_manage_error(error, err_count=1):
    import arbtaker_settings as settings
    err_type = type(error).__name__
    print("ccxt_manage_error", type(error), err_type, error)
    if settings.dry_mode:
        time.sleep(2 * err_count)
    else:
        if (err_type == "NetworkError" or
                err_type == "DDoSProtection" or
                err_type == "RateLimitExceeded" or
                err_type == "InvalidNonce" or
                err_type == "RequestTimeout" or
                err_type == "ExchangeNotAvailable" or
                err_type == "Errno -3" or
                err_type == "AuthenticationError" or
                err_type == "Temporary failure in name resolution" or
                err_type == "ExchangeError" or
                err_type == "BadResponse"):
            time.sleep(err_count * 2)
        # debug
        # elif err_type == "InsufficientFunds" or "BadSymbol":
        #     return False
        # debug
        else:
            exit()


def ccxt_call_fetch_order_book(symbol, ccxt_o, limit=25):
    timer_perf = time.time()
    err_count = 0
    while True:
        try:
            result = ccxt_o.fetch_order_book(symbol, limit)
        except Exception as error:
            err_count += 1
            ccxt_manage_error(error, err_count)
        else:
            if settings.debug >= 2:
                print("ccxt_call_fetch_order_book(", symbol, ", ", limit,
                      "), timer_perf: " + str(time.time() - timer_perf))
            return result


def ccxt_call_fetch_order(order_id, ccxt_o):
    timer_perf = time.time()
    err_count = 0
    while True:
        try:

            result = ccxt_o.fetch_order(order_id)
        except Exception as error:
            err_count += 1
            ccxt_manage_error(error, err_count)
        else:
            if settings.debug >= 2:
                print("ccxt_call_fetch_order(", order_id, "), timer_perf: " + str(time.time() - timer_perf))
            return result


def ccxt_call_create_limit_order(side, symbol, amount, price, ccxt_o):
    # "side1" = BUY DX SELL CEX
    # "side2" = SELL DX BUY CEX
    timer_perf = time.time()
    max_ccxt_call_time = 120
    err_count = 0
    if side == "SELL":
        while True:
            if time.time() - timer_perf >= max_ccxt_call_time:
                message = "ccxt_call_create_limit_order(" + side + ", " + symbol + ", " + str(amount) + ", " + str(
                    price) + "), timer > max_ccxt_call_time, cancel all orders and exit()"
                print(message)
                ccxt_log.error(message)
                # dex_cancel_all_my_open_orders()
                exit()  # won't retry
            try:
                result = ccxt_o.create_limit_sell_order(symbol, amount, price)
            except Exception as error:
                err_count += 1
                ccxt_manage_error(error, err_count)
            else:
                if settings.debug >= 2:
                    print("ccxt_call_create_limit_order(", side, symbol, amount, price,
                          "), timer_perf: " + str(time.time() - timer_perf))
                return result
    elif side == "BUY":
        while True:
            if time.time() - timer_perf >= max_ccxt_call_time:
                message = "ccxt_call_create_limit_order(" + side + ", " + symbol + ", " + str(amount) + ", " + str(
                    price) + "), timer > max_ccxt_call_time, cancel all orders and exit()"
                print(message)
                ccxt_log.error(message)
                # dex_cancel_all_my_open_orders()
                exit()  # won't retry
            try:

                result = ccxt_o.create_limit_buy_order(symbol, amount, price)
            except Exception as error:
                err_count += 1
                ccxt_manage_error(error, err_count)

            else:
                if settings.debug >= 2:
                    print("ccxt_call_create_limit_order(", side, symbol, amount, price,
                          "), timer_perf: " + str(time.time() - timer_perf))
                return result


def ccxt_call_fetch_free_balance(ccxt_o):
    timer_perf = time.time()
    max_ccxt_call_time = 120
    err_count = 0
    while True:
        if time.time() - timer_perf >= max_ccxt_call_time:
            message = "ccxt_call_fetch_free_balance(), timer > max_ccxt_call_time, cancel all orders and exit()"
            print(message)
            ccxt_log.error(message)
            # dex_cancel_all_my_open_orders()
            exit()  # won't retry
        try:

            result = ccxt_o.fetch_free_balance()
        except Exception as error:
            err_count += 1
            ccxt_manage_error(error, err_count)
        else:
            if settings.debug >= 2:
                print("ccxt_call_fetch_free_balance(), timer_perf: " + str(time.time() - timer_perf))
            return result
