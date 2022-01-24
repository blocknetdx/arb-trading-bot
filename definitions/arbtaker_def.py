import datetime
import os
import time

if not os.path.isdir('logs'):
    os.mkdir('logs')
import definitions.ccxt_funcs_def as ccxt
import arbtaker_settings as settings
import definitions.xbridge_funcs_def as xb
import definitions.logger as logger
import logging

from utils.contracts import tokens, contracts
from utils.pangolin import Pangolin

taker_logger = logger.setup_logger(name="GENERAL_LOG", log_file='logs/arb_TAKER.log', level=logging.INFO)
taker_balance_logger = logger.setup_logger(name="BALANCES_LOG", log_file='logs/arb_TAKER_balances.log',
                                           level=logging.INFO)


class Coin:
    def __init__(self, coin_name, dex_enabled=True):
        self.name = coin_name
        self.cex = Cex()
        self.dex_enabled = dex_enabled
        self.dex = Dex()
        self.amm = Amm()

    def dx_update_orderbook(self, taker_o):
        self.dex.asks_ob, self.dex.bids_ob = dx_update_orderbook(self.name, taker_o.name)

    def dx_get_new_address(self):
        if self.dex_enabled:
            result = xb.dx_call_getnewtokenadress(self.name)
            self.dex.active_address = result[0]
            dx_settings_save_new_address(self)

    def dx_select_order(self, maker_o, taker_o):
        # scout DX orderbook for conform active order, else set all at -1
        orderbook = []
        if "BUY" in self.dex.side:
            orderbook = self.dex.asks_ob
        elif "SELL" in self.dex.side:
            orderbook = self.dex.bids_ob
        if self.name in settings.max_size:
            max_maker_amount = settings.max_size[self.name]
        else:
            max_maker_amount = -1
        if taker_o.name in settings.max_size:
            max_taker_amount = settings.max_size[taker_o.name]
        else:
            max_taker_amount = -1

        for order in orderbook:
            order_status = xb.dx_call_getorderstatus(order[2])
            if 'status' in order_status and "exact" in order_status['order_type'] and \
                    order[2] not in maker_o.dex.order_blacklist:
                if "BUY" in self.dex.side:
                    if taker_o.dex.balance > 0 or settings.dry_mode:
                        maker_amount = float(order_status['maker_size'])
                        taker_amount = float(order_status['taker_size'])
                        if (max_taker_amount != -1 and taker_amount < max_taker_amount) or max_taker_amount == -1 or \
                                settings.dry_mode:
                            if (max_maker_amount != -1 and maker_amount < max_maker_amount) or \
                                    max_maker_amount == -1 or settings.dry_mode:
                                if taker_amount < taker_o.dex.balance or settings.dry_mode:
                                    self.dex.order = order
                                    self.dex.maker_amount = maker_amount
                                    self.dex.taker_amount = taker_amount
                                    break
                                else:
                                    print("taker_amount < taker_o.dex.balance FALSE", taker_amount, taker_o.dex.balance)
                            else:
                                print("invalid order, maker size", self.dex.side, self.name, maker_amount,
                                      max_maker_amount)
                                self.dex.order_blacklist.append(order[2])
                                print("blacklist", order[2])
                        else:
                            print("invalid order, taker size", self.dex.side, taker_o.name, taker_amount,
                                  max_taker_amount)
                            self.dex.order_blacklist.append(order[2])
                            print("blacklist", order[2])
                elif "SELL" in self.dex.side:
                    if maker_o.dex.balance > 0 or settings.dry_mode:
                        maker_amount = float(order_status['taker_size'])
                        taker_amount = float(order_status['maker_size'])
                        if (max_taker_amount != -1 and taker_amount < max_taker_amount) or max_taker_amount == -1 or \
                                settings.dry_mode:
                            if (max_maker_amount != -1 and maker_amount < max_maker_amount) or \
                                    max_maker_amount == -1 or settings.dry_mode:
                                if maker_amount < maker_o.dex.balance or settings.dry_mode:
                                    self.dex.order = order
                                    self.dex.maker_amount = maker_amount
                                    self.dex.taker_amount = taker_amount
                                    break
                                else:
                                    print("maker_amount < maker_o.dex.balance FALSE", maker_amount, maker_o.dex.balance)
                            else:
                                print("invalid order, maker size", self.dex.side, self.name, maker_amount,
                                      max_maker_amount)
                                self.dex.order_blacklist.append(order[2])
                                print("blacklist", order[2])
                        else:
                            print("invalid order, taker size", self.dex.side, taker_o.name, taker_amount,
                                  max_taker_amount)
                            self.dex.order_blacklist.append(order[2])
                            print("blacklist", order[2])
        if self.dex.maker_amount == -1:
            print(" " * 3, "Dex", self.dex.side, "No valid order to select")
        else:
            print(" " * 3, "Dex", self.dex.side, "Order selected: ", end='')
            print(self.dex.order)

    def cex_update_orderbook(self, ccxt_o=None):
        # side s1 s2
        update_delay = 3
        if 'BTC' not in self.name and ccxt_o is not None:
            if self.cex.orderbook_timer is None or time.time() - self.cex.orderbook_timer > update_delay:
                self.cex.orderbook = ccxt.ccxt_call_fetch_order_book(self.name + '/BTC', ccxt_o)
                self.cex.orderbook_timer = time.time()
                print("updated", self.name + "/BTC cex orderbook")


class Cex:
    def __init__(self):
        self.symbol_s1 = None
        self.symbol_s2 = None
        self.executed_tobtc_s1 = -1
        self.executed_tobtc_s2 = -1
        self.final_price_cex_book_s1 = -1
        self.final_price_cex_book_s2 = -1
        self.side_s1 = ""
        self.side_s2 = ""
        self.balance = 0
        self.average_price_s1 = -1
        self.average_price_s2 = -1
        self.orderbook = None
        self.orderbook_timer = None

    def set_balance(self, balance):
        if (isinstance(balance, float) or isinstance(balance, int)) and balance >= 0:
            self.balance = float('{:.6f}'.format(balance))
        else:
            self.balance = None

    def reset_side(self):
        self.side_s1 = ""
        self.side_s2 = ""
        self.executed_tobtc_s1 = -1
        self.executed_tobtc_s2 = -1
        self.final_price_cex_book_s1 = -1
        self.final_price_cex_book_s2 = -1
        self.average_price_s1 = -1
        self.average_price_s2 = -1


class Dex:
    def __init__(self):
        self.balance = 0
        self.order = None
        self.side = ""
        self.maker_amount = -1
        self.taker_amount = -1
        self.asks_ob = None
        self.bids_ob = None
        self.active_address = None
        self.order_blacklist = []

    def set_balance(self, balance):
        if (isinstance(balance, float) or isinstance(balance, int)) and balance >= 0:
            self.balance = balance
        else:
            self.balance = None

    def reset_order(self):
        self.order = None
        # self.side = ""
        self.maker_amount = -1
        self.taker_amount = -1
        self.asks_ob = None
        self.bids_ob = None

class Amm:
    def __init__(self):
        self.balance = 0

    def set_balance(self, balance):
        if (isinstance(balance, float) or isinstance(balance, int)) and balance >= 0:
            self.balance = balance
        else:
            self.balance = None

def main_init_coins_list():
    coins_list = []
    dx_tokens = xb.dx_call_dxgetlocaltokens()
    for token_name in dx_tokens:
        if "Wallet" not in token_name:
            if token_name in settings.dex_coins_disabled:
                coins_list.append(Coin(token_name, dex_enabled=False))
            else:
                coins_list.append(Coin(token_name))
    if not any(x for x in coins_list if x.name == "BTC"):
        coins_list.append(Coin("BTC", dex_enabled=False))
    return coins_list


def update_balances_dx(coins_list):
    dx_bals = xb.dx_call_gettokensbalance()
    for coin in coins_list:  # dx_bals:
        # coin_obj = next((x for x in coins_list if x.name == coin), None)
        if coin.name in dx_bals:
            coin.dex.set_balance(float(dx_bals[coin.name]))
        else:
            print(coin.name, "missing from dex balance")


def update_balances_cex(coins_list, ccxt_instance):
    cex_bals = ccxt.ccxt_call_fetch_free_balance(ccxt_instance)
    for coin in coins_list:
        if coin.name in cex_bals:
            coin.cex.set_balance(float(cex_bals[coin.name]))


def update_balance_pang(coin_list, avax_instance):
    pang_list_coins = tokens
    for coin in coin_list:
        if coin.name.lower() in pang_list_coins:
            token = pang_list_coins[coin.name.lower()]
            balance = avax_instance.get_token_balance(contracts[token])/10**8
            coin.amm.set_balance(float(balance))


def dx_get_active_dx_markets(coins_list=None,
                             preferred_token2=None):  # Prioritize this preferred_token2  list as coin2 if possible
    if preferred_token2 is None:
        preferred_token2 = ["BTC", "LTC"]
    temp_markets_list = []
    print("Listing DX markets and retrieving orderbook:")
    for token1 in coins_list:
        for token2 in coins_list:
            if token1.name != token2.name and token1.dex_enabled and token2.dex_enabled:
                pairing_exist = any(x for x in temp_markets_list if (x[0] == token1.name and x[1] == token2.name) or (
                        x[0] == token2.name and x[1] == token1.name))
                if not pairing_exist:
                    if token1.name in preferred_token2:
                        if token1.name in preferred_token2 and token2.name in preferred_token2:
                            index1 = preferred_token2.index(token1.name)
                            index2 = preferred_token2.index(token2.name)
                            if index1 > index2:
                                t1 = token1.name
                                t2 = token2.name
                            else:
                                t1 = token2.name
                                t2 = token1.name
                        else:
                            t1 = token2.name
                            t2 = token1.name
                    else:
                        t1 = token1.name
                        t2 = token2.name
                    temp_markets_list.append([t1, t2])
    active_markets_list = []
    for market in temp_markets_list:
        if market[0] not in settings.dex_coins_disabled and market[1] not in \
                settings.dex_coins_disabled:
            orderbook = xb.dx_call_getorderbook(market[0], market[1], detail=3)
            if orderbook['asks'] or orderbook['bids']:
                del orderbook['detail']
                active_markets_list.append(orderbook)
            else:
                print(market[0] + "/" + market[1], "no orders on DX")
    return active_markets_list


def dx_update_orderbook(maker, taker, detail=3):
    orderbook = xb.dx_call_getorderbook(maker, taker, detail=detail)
    bids = []
    asks = []
    if 'asks' in orderbook and orderbook['asks']:
        # del orderbook['detail']
        asks = orderbook['asks']
        asks.reverse()
    if 'bids' in orderbook and orderbook['bids']:
        # del orderbook['detail']
        bids = orderbook['bids']
    return asks, bids


def calc_cex_path(maker_o, taker_o):
    ccxt_token1 = None
    ccxt_token2 = None
    ccxt_token3 = None
    if "BTC" not in maker_o.name and "BTC" not in taker_o.name:
        ccxt_token1 = maker_o.name
        ccxt_token2 = "BTC"
        ccxt_token3 = taker_o.name
    elif "BTC" in maker_o.name and "BTC" not in taker_o.name:
        ccxt_token1 = taker_o.name
        ccxt_token2 = maker_o.name
    elif "BTC" not in maker_o.name and "BTC" in taker_o.name:
        ccxt_token1 = maker_o.name
        ccxt_token2 = taker_o.name

    print(ccxt_token1, ccxt_token2, ccxt_token3)
    if ccxt_token3:
        ccxt_symbol1 = ccxt_token1 + "/" + ccxt_token2
        ccxt_symbol2 = ccxt_token3 + "/" + ccxt_token2
    else:
        ccxt_symbol1 = ccxt_token1 + "/" + ccxt_token2
        ccxt_symbol2 = None
    maker_o.cex.symbol_s1 = ccxt_symbol1
    maker_o.cex.symbol_s2 = ccxt_symbol2


def check_valid_symbols(cex_symbol1=None, cex_symbol2=None, ccxt_o=None):
    if cex_symbol1 and cex_symbol1 not in ccxt_o.symbols:
        print(ccxt_o.name, "symbol not supported:", cex_symbol1)
        settings.dex_coins_disabled.append(cex_symbol1[0:cex_symbol1.find("/")])
        print(settings.dex_coins_disabled)
        return False
    if cex_symbol2 and cex_symbol2 not in ccxt_o.symbols:
        print(cex_symbol2[cex_symbol2.find("/") + 1:len(cex_symbol2)])
        settings.dex_coins_disabled.append(cex_symbol2[cex_symbol2.find("/") + 1:len(cex_symbol2)])
        print(ccxt_o.name, "symbol not supported:", cex_symbol2)
        print(settings.dex_coins_disabled)
        return False
    return True


def calc_cex_coin1_depth_price(side, cex_symbol, orderbook, qty, ccxt_o):
    # side: bids or asks
    # input coin1 qty
    count = 0
    final_price_cex_book = 0
    while final_price_cex_book == 0:
        final_price_cex_book = 0
        quantity = qty
        executed_tobtc = 0
        count += 1
        if count == 2:
            message = "calc_cex_depth_price(" + cex_symbol + ", " + ccxt_o.name + ", " + str(qty) + \
                      " ) " + side + " error, count = " + str(count) + ", " + str(final_price_cex_book)
            print(message)
            orderbook = ccxt.ccxt_call_fetch_order_book(cex_symbol, ccxt_o, 500)
        elif count == 3:
            print("calc_cex_coin1_depth_price, not enough depth on orderbook")
            return None, None
        for order in orderbook[side]:
            if order[1] > quantity:
                executed_quantity = quantity
                quantity = 0
                executed_tobtc += executed_quantity * order[0]
            elif order[1] <= quantity:
                executed_quantity = order[1]
                quantity -= executed_quantity
                executed_tobtc += executed_quantity * order[0]
            if quantity == 0:
                final_price_cex_book = order[0]
                break
        if quantity == 0 and final_price_cex_book > 0:
            return executed_tobtc, final_price_cex_book


def get_coin_btc_price(orderbook):
    rate = 0
    ask = float(orderbook["asks"][0][0])
    bid = float(orderbook["bids"][0][0])
    if ask > bid:
        rate = bid + (ask - bid) / 2
    elif ask < bid:
        rate = ask + (bid - ask) / 2
    elif ask == bid:
        rate = ask
    return rate


def balance_check(side, maker_o=None, taker_o=None, btc_o=None):
    # side 'dx'/'s1'/'s2'
    #       buy sell buy
    #       sell buy sell
    if 's1' in side:
        if "SELL" in maker_o.cex.side_s1:
            if settings.min_size['BTC'] < maker_o.cex.executed_tobtc_s1 < settings.max_size['BTC'] or \
                    settings.dry_mode:
                if maker_o.cex.executed_tobtc_s1 < btc_o.cex.balance or settings.dry_mode:
                    return True
                else:
                    print("maker_o.cex.executed_tobtc_s1 < btc_o.cex.balance FALSE", maker_o.cex.executed_tobtc_s1,
                          btc_o.cex.balance)
            else:
                print("min_size['BTC'] < executed_tobtc_s1 < max_size['BTC'] FALSE", settings.min_size['BTC'],
                      maker_o.cex.executed_tobtc_s1, settings.max_size['BTC'])
            maker_o.dex.order_blacklist.append(maker_o.dex.order[2])
            print("blacklist", maker_o.dex.order[2])
            return False
        elif "BUY" in maker_o.cex.side_s1:
            if settings.min_size['BTC'] < maker_o.cex.executed_tobtc_s1 < settings.max_size['BTC'] or \
                    settings.dry_mode:
                if maker_o.dex.maker_amount < maker_o.cex.balance or settings.dry_mode:
                    return True
                else:
                    print("maker_o.dex.maker_amount < maker_o.cex.balance FALSE", maker_o.dex.maker_amount,
                          maker_o.cex.balance)
            else:
                print("min_size['BTC'] < maker_o.cex.executed_tobtc_s1 < max_size['BTC'] FALSE",
                      settings.min_size['BTC'], maker_o.cex.executed_tobtc_s1,
                      settings.max_size['BTC'])
            maker_o.dex.order_blacklist.append(maker_o.dex.order[2])
            print("blacklist", maker_o.dex.order[2])
            return False
    elif 's2' in side:
        if "SELL" in maker_o.cex.side_s2:
            if maker_o.dex.taker_amount < taker_o.cex.balance or settings.dry_mode:
                return True
            else:
                print("maker_o.dex.taker_amount < taker_o.cex.balance FALSE", maker_o.dex.taker_amount,
                      taker_o.cex.balance)
                maker_o.dex.order_blacklist.append(maker_o.dex.order[2])
                print("blacklist", maker_o.dex.order[2])
                return False
        elif "BUY" in maker_o.cex.side_s2:
            if maker_o.cex.executed_tobtc_s2 < btc_o.cex.balance or settings.dry_mode:
                return True
            else:
                print("maker_o.cex.executed_tobtc_s2 < btc_o.cex.balance FALSE", maker_o.cex.executed_tobtc_s2,
                      btc_o.cex.balance)
                maker_o.dex.order_blacklist.append(maker_o.dex.order[2])
                print("blacklist", maker_o.dex.order[2])
                return False


def calc_arb_direct(maker_o, taker_o, coins_list, ccxt_o):
    print(f"{' ' * 10}{'XBRIDGE':<19}{': ' + maker_o.name + '/' + taker_o.name}")
    calc_cex_path(maker_o, taker_o)
    print(f"{' ' * 10}{'CEX hop':<19}{': ' + maker_o.cex.symbol_s1}")
    btc_o = next(x for x in coins_list if x.name == 'BTC')
    if (maker_o.dex.asks_ob or maker_o.dex.bids_ob) and check_valid_symbols(maker_o.cex.symbol_s1, ccxt_o=ccxt_o):
        maker_o.cex_update_orderbook(ccxt_o)
    else:
        return False
    if maker_o.dex.asks_ob:
        maker_o.cex.reset_side()
        # i buy block on dx, sell block on cex
        maker_o.dex.side = "BUY"
        maker_o.cex.side_s1 = "SELL"
        maker_o.dx_select_order(maker_o=maker_o,
                                taker_o=taker_o)
        if maker_o.dex.maker_amount != -1:
            maker_o.cex.executed_tobtc_s1, maker_o.cex.final_price_cex_book_s1 = calc_cex_coin1_depth_price(side="bids",
                                                                                                            cex_symbol=maker_o.cex.symbol_s1,
                                                                                                            orderbook=maker_o.cex.orderbook,
                                                                                                            qty=maker_o.dex.maker_amount,
                                                                                                            ccxt_o=ccxt_o)
            if maker_o.cex.executed_tobtc_s1 and maker_o.cex.final_price_cex_book_s1 and \
                    balance_check('s1', maker_o, taker_o, btc_o):
                maker_o.cex.average_price_s1 = maker_o.cex.executed_tobtc_s1 / maker_o.dex.maker_amount
                profit_percent = maker_o.cex.executed_tobtc_s1 / maker_o.dex.taker_amount  # 1=100%
                msg3_pr = f"{'':<12}PROFIT : {'{:.8f}'.format(maker_o.cex.executed_tobtc_s1):<10} - {'{:.8f}'.format(maker_o.dex.taker_amount):<10} = {'{:.8f}'.format(maker_o.cex.executed_tobtc_s1 - maker_o.dex.taker_amount):<10} = {'{:.2f}'.format(profit_percent * 100 - 100)} %"
                msg1_dx = f"{' ' * 10}{'Xbridge(' + maker_o.name + '/' + taker_o.name + ')':<19}: {'BUY':<5}{'{:.8f}'.format(maker_o.dex.maker_amount):<13} {maker_o.name:<6}{'SELL':<5}{'{:.8f}'.format(maker_o.dex.taker_amount):<11} {taker_o.name:<6}"  # {'convert to cex price ' + '{:.8f}'.format(maker_o.dex.taker_amount * coin2_cex_btcrate)}"
                msg2_s1 = f"{' ' * 10}{ccxt_o.name + '(' + maker_o.cex.symbol_s1 + ')':<19}: {'SELL':<5}{'{:.8f}'.format(maker_o.dex.maker_amount):<13} {maker_o.name:<6}{'BUY':<5}{'{:.8f}'.format(maker_o.cex.executed_tobtc_s1):<11} {'BTC':<4}{'AVG_PRICE:':<11}{'{:.8f}'.format(maker_o.cex.average_price_s1)}"
                print(msg1_dx + "\n" + msg2_s1 + "\n" + msg3_pr)
                # TX FEE PROTECTION WHEN BUYING COIN1 WITH BTC
                if 'BTC' in taker_o.name and settings.min_profit < 1.1:
                    min_profit = 1.1
                else:
                    min_profit = settings.min_profit

                if profit_percent > min_profit:
                    taker_logger.critical("\n" + msg1_dx + "\n" + msg2_s1 + "\n" + msg3_pr)
                    print("profitable ARB!")
                    return True
                else:
                    maker_o.cex.reset_side()
    else:
        print(" " * 3, "Dex BUY No order on book")
    if maker_o.dex.bids_ob:
        # i sell block on dx, buy block on cex
        maker_o.dex.side = "SELL"
        maker_o.cex.side_s1 = "BUY"
        # maker_o.cex.side_s2 = "SELL"
        maker_o.dx_select_order(maker_o=maker_o,
                                taker_o=taker_o)
        if maker_o.dex.maker_amount != -1:
            maker_o.cex.executed_tobtc_s1, maker_o.cex.final_price_cex_book_s1 = calc_cex_coin1_depth_price(side="asks",
                                                                                                            cex_symbol=maker_o.cex.symbol_s1,
                                                                                                            orderbook=maker_o.cex.orderbook,
                                                                                                            qty=maker_o.dex.maker_amount,
                                                                                                            ccxt_o=ccxt_o)
            if maker_o.cex.executed_tobtc_s1 and maker_o.cex.final_price_cex_book_s1 and balance_check('s1', maker_o, taker_o, btc_o):
                maker_o.cex.average_price_s1 = maker_o.cex.executed_tobtc_s1 / maker_o.dex.maker_amount
                profit_percent = maker_o.dex.taker_amount / maker_o.cex.executed_tobtc_s1
                msg1_dx = f"{' ' * 10}{'Xbridge(' + maker_o.name + '/' + taker_o.name + ')':<19}: {'SELL':<5}{'{:.8f}'.format(maker_o.dex.maker_amount):<13} {maker_o.name:<6}{'BUY':<5}{'{:.8f}'.format(maker_o.dex.taker_amount):<11} {taker_o.name:<6}"
                msg2_s1 = f"{' ' * 10}{ccxt_o.name + '(' + maker_o.cex.symbol_s1 + ')':<19}: {'BUY':<5}{'{:.8f}'.format(maker_o.dex.maker_amount):<13} {maker_o.name:<6}{'SELL':<5}{'{:.8f}'.format(maker_o.cex.executed_tobtc_s1):<11} {'BTC':<4}{'AVG_PRICE:':<11}{'{:.8f}'.format(maker_o.cex.average_price_s1)}"
                msg3_pr = f"{' ' * 10}{'':<12}PROFIT : {'{:.8f}'.format(maker_o.dex.taker_amount):<10} - {'{:.8f}'.format(maker_o.cex.executed_tobtc_s1):<10} = {'{:.8f}'.format(maker_o.dex.taker_amount - maker_o.cex.executed_tobtc_s1):<10} = {'{:.2f}'.format(profit_percent * 100 - 100)} %"
                print(msg1_dx + "\n" + msg2_s1 + "\n" + msg3_pr)
                if profit_percent > settings.min_profit:
                    taker_logger.critical("\n" + msg1_dx + "\n" + msg2_s1 + "\n" + msg3_pr)
                    print("profitable ARB!")
                    return True
                else:
                    maker_o.cex.reset_side()
    else:
        print(" " * 3, "Dex SELL No order on book")
    return False


def calc_arb_triway(maker_o, taker_o, coins_list, ccxt_o):
    print(f"{'XBRIDGE':<19}{': ' + maker_o.name + '/' + taker_o.name}")
    calc_cex_path(maker_o, taker_o)
    print(f"{'CEX hop':<19}{': ' + maker_o.cex.symbol_s1 + ' | ' + maker_o.cex.symbol_s2}")
    btc_o = next(x for x in coins_list if x.name == 'BTC')
    if (maker_o.dex.asks_ob or maker_o.dex.bids_ob) and check_valid_symbols(maker_o.cex.symbol_s1,
                                                                            maker_o.cex.symbol_s2, ccxt_o):
        maker_o.cex_update_orderbook(ccxt_o)
        if maker_o.cex.symbol_s2:
            taker_o.cex_update_orderbook(ccxt_o)
        else:
            return False
    else:
        return False
    if maker_o.dex.asks_ob:
        maker_o.cex.reset_side()
        # i buy block on dx, sell block on cex
        maker_o.dex.side = "BUY"
        maker_o.cex.side_s1 = "SELL"
        maker_o.cex.side_s2 = "BUY"
        maker_o.dx_select_order(maker_o=maker_o,
                                taker_o=taker_o)
        if maker_o.dex.maker_amount != -1:
            maker_o.cex.executed_tobtc_s1, maker_o.cex.final_price_cex_book_s1 = calc_cex_coin1_depth_price(side="bids",
                                                                                                            cex_symbol=maker_o.cex.symbol_s1,
                                                                                                            orderbook=maker_o.cex.orderbook,
                                                                                                            qty=maker_o.dex.maker_amount,
                                                                                                            ccxt_o=ccxt_o)
            if maker_o.cex.executed_tobtc_s1 and maker_o.cex.final_price_cex_book_s1 and \
                    balance_check('s1', maker_o, taker_o, btc_o):
                maker_o.cex.average_price_s1 = maker_o.cex.executed_tobtc_s1 / maker_o.dex.maker_amount
                maker_o.cex.executed_tobtc_s2, maker_o.cex.final_price_cex_book_s2 = calc_cex_coin1_depth_price(
                    side="asks",
                    cex_symbol=maker_o.cex.symbol_s2,
                    orderbook=taker_o.cex.orderbook,
                    qty=maker_o.dex.taker_amount,
                    ccxt_o=ccxt_o)
                if maker_o.cex.executed_tobtc_s2 and maker_o.cex.final_price_cex_book_s2 and \
                        balance_check('s2', maker_o, taker_o, btc_o):
                    maker_o.cex.average_price_s2 = maker_o.cex.executed_tobtc_s2 / maker_o.dex.taker_amount
                    msg1_dx = f"{'Xbridge(' + maker_o.name + '/' + taker_o.name + ')':<19}: {'BUY':<5}{'{:.8f}'.format(maker_o.dex.maker_amount):<13} {maker_o.name:<6}{'SELL':<5}{'{:.8f}'.format(maker_o.dex.taker_amount):<11} {taker_o.name:<6}"  # {'convert to cex price ' + '{:.8f}'.format(maker_o.dex.taker_amount * coin2_cex_btcrate)}"
                    msg2_s1 = f"{ccxt_o.name + '(' + maker_o.cex.symbol_s1 + ')':<19}: {'SELL':<5}{'{:.8f}'.format(maker_o.dex.maker_amount):<13} {maker_o.name:<6}{'BUY':<5}{'{:.8f}'.format(maker_o.cex.executed_tobtc_s1):<11} {'BTC':<4}{'AVG_PRICE:':<11}{'{:.8f}'.format(maker_o.cex.average_price_s1)}"
                    msg3_s2 = f"{ccxt_o.name + '(' + maker_o.cex.symbol_s2 + ')':<19}: {'BUY':<5}{'{:.8f}'.format(maker_o.dex.taker_amount):<13} {taker_o.name:<6}{'SELL':<5}{'{:.8f}'.format(maker_o.cex.executed_tobtc_s2):<11} {'BTC':<4}{'AVG_PRICE:':<11}{'{:.8f}'.format(maker_o.cex.average_price_s2)}"
                    profit_percent = maker_o.cex.executed_tobtc_s1 / maker_o.cex.executed_tobtc_s2  # 1=100%
                    msg4_pr = f"{'':<12}PROFIT : {'{:.8f}'.format(maker_o.cex.executed_tobtc_s1):<10} - {'{:.8f}'.format(maker_o.cex.executed_tobtc_s2):<10} = {'{:.8f}'.format(maker_o.cex.executed_tobtc_s1 - maker_o.cex.executed_tobtc_s2):<10} = {'{:.2f}'.format(profit_percent * 100 - 100)} %"
                    print(msg1_dx + "\n" + msg2_s1 + "\n" + msg3_s2 + "\n" + msg4_pr)
                    if profit_percent > settings.min_profit:
                        taker_logger.critical("\n" + msg1_dx + "\n" + msg2_s1 + "\n" + msg3_s2 + "\n" + msg4_pr)
                        print("profitable ARB!")
                        return True
                    else:
                        maker_o.cex.reset_side()
    else:
        print(" " * 3, "Dex BUY No order on book")

    if maker_o.dex.bids_ob:
        # i sell block on dx, buy block on cex
        maker_o.dex.side = "SELL"
        maker_o.cex.side_s1 = "BUY"
        maker_o.cex.side_s2 = "SELL"
        maker_o.dx_select_order(maker_o=maker_o,
                                taker_o=taker_o)
        if maker_o.dex.maker_amount != -1:
            maker_o.cex.executed_tobtc_s1, maker_o.cex.final_price_cex_book_s1 = calc_cex_coin1_depth_price(side="asks",
                                                                                                            cex_symbol=maker_o.cex.symbol_s1,
                                                                                                            orderbook=maker_o.cex.orderbook,
                                                                                                            qty=maker_o.dex.maker_amount,
                                                                                                            ccxt_o=ccxt_o)
            if maker_o.cex.executed_tobtc_s1 and  maker_o.cex.final_price_cex_book_s1 and \
                    balance_check('s1', maker_o, taker_o, btc_o):
                maker_o.cex.average_price_s1 = maker_o.cex.executed_tobtc_s1 / maker_o.dex.maker_amount
                maker_o.cex.executed_tobtc_s2, maker_o.cex.final_price_cex_book_s2 = calc_cex_coin1_depth_price(
                    side="bids",
                    cex_symbol=maker_o.cex.symbol_s2,
                    orderbook=taker_o.cex.orderbook,
                    qty=maker_o.dex.taker_amount,
                    ccxt_o=ccxt_o)
                if maker_o.cex.executed_tobtc_s2 and maker_o.cex.final_price_cex_book_s2 and \
                        balance_check('s2', maker_o, taker_o, btc_o):
                    maker_o.cex.average_price_s2 = maker_o.cex.executed_tobtc_s2 / maker_o.dex.taker_amount
                    msg1_dx = f"{'Xbridge(' + maker_o.name + '/' + taker_o.name + ')':<19}: {'SELL':<5}{'{:.8f}'.format(maker_o.dex.maker_amount):<13} {maker_o.name:<6}{'BUY':<5}{'{:.8f}'.format(maker_o.dex.taker_amount):<11} {taker_o.name:<6}"
                    msg2_s1 = f"{ccxt_o.name + '(' + maker_o.cex.symbol_s1 + ')':<19}: {'BUY':<5}{'{:.8f}'.format(maker_o.dex.maker_amount):<13} {maker_o.name:<6}{'SELL':<5}{'{:.8f}'.format(maker_o.cex.executed_tobtc_s1):<11} {'BTC':<4}{'AVG_PRICE:':<11}{'{:.8f}'.format(maker_o.cex.average_price_s1)}"
                    msg3_s2 = f"{ccxt_o.name + '(' + maker_o.cex.symbol_s2 + ')':<19}: {'SELL':<5}{'{:.8f}'.format(maker_o.dex.taker_amount):<13} {taker_o.name:<6}{'BUY':<5}{'{:.8f}'.format(maker_o.cex.executed_tobtc_s2):<11} {'BTC':<4}{'AVG_PRICE:':<11}{'{:.8f}'.format(maker_o.cex.average_price_s2)}"
                    profit_percent = maker_o.cex.executed_tobtc_s2 / maker_o.cex.executed_tobtc_s1
                    msg4_pr = f"{'':<12}PROFIT : {'{:.8f}'.format(maker_o.cex.executed_tobtc_s2):<10} - {'{:.8f}'.format(maker_o.cex.executed_tobtc_s1):<10} = {'{:.8f}'.format(maker_o.cex.executed_tobtc_s2 - maker_o.cex.executed_tobtc_s1):<10} = {'{:.2f}'.format(profit_percent * 100 - 100)} %"
                    print(msg1_dx + "\n" + msg2_s1 + "\n" + msg3_s2 + "\n" + msg4_pr)
                    if profit_percent > settings.min_profit:
                        taker_logger.critical("\n" + msg1_dx + "\n" + msg2_s1 + "\n" + msg3_s2 + "\n" + msg4_pr)
                        print("profitable ARB!")
                        return True
                    else:
                        maker_o.cex.reset_side()
    else:
        print(" " * 3, "Dex SELL No order on book")
    return False


def dx_set_addresses(coins_list):
    for coin in coins_list:
        if coin.dex_enabled:
            if coin.name in settings.dx_addresses:
                coin.dex.active_address = settings.dx_addresses[coin.name]
            else:
                result = xb.dx_call_getnewtokenadress(coin.name)
                print(result)
                coin.dex.active_address = result[0]
                dx_settings_save_new_address(coin)


def dx_settings_save_new_address(coin):
    filename = "arbtaker_settings.py"
    with open(filename, "r") as fileread:
        file = fileread.readlines()
        if "dx_addresses[\'" + coin.name + "\']" not in file:
            index = file.index("dx_addresses = {}\n")
            file.insert(index + 1, 'dx_addresses[\'' + coin.name + '\'] = "' + coin.dex.active_address + '"\n')
            with open(filename, "w") as filewrite:
                filewrite.writelines(file)
        else:
            index = file.index("dx_addresses[\'" + coin.name + "\']")
            file[index] = 'dx_addresses[\'' + coin.name + '\'] = "' + coin.dex.active_address + '"\n'
            with open(filename, "w") as filewrite:
                filewrite.writelines(file)


def dx_check_inprogress_order(maker_o):
    # return 1 if order finished, 0 if still in progress, -1 if error, -2 still open after take
    dx_done = 0
    timer_print = time.time()
    timer_lenght = time.time()
    sleep_time = 1
    count = 0
    dx_refresh = 0
    while dx_done == 0:
        dx_refresh = xb.dx_call_getorderstatus(maker_o.dex.order[2])
        count += 1
        if 'status' in dx_refresh:
            if count % 10 == 0:
                print("dx_order:", maker_o.dex.order[2], "status:", dx_refresh['status'])
            if 'finished' in dx_refresh['status']:
                dx_done = 1
            elif 'expired' in dx_refresh['status']:
                dx_done = -1
            elif 'offline' in dx_refresh['status']:
                dx_done = -1
            elif 'canceled' in dx_refresh['status']:
                dx_done = -1
            elif 'invalid' in dx_refresh['status']:
                dx_done = -1
            elif "rolled back" in dx_refresh['status']:
                dx_done = -1
            elif "rollback failed" in dx_refresh['status']:
                dx_done = -1
            elif "open" in dx_refresh['status'] and count > 5:
                dx_done = -2
            elif "initialized" in dx_refresh['status']:
                if time.time() - timer_lenght > 2 * 60:
                    message = "dx_order: " + maker_o.dex.order[2] + " status: " + dx_refresh['status'] + \
                              " bot timeout, cancel"
                    print(message)
                    taker_logger.error(message)
                    xb.dx_call_cancelorder(maker_o.dex.order[2])
        time.sleep(sleep_time)
    message = "dx_order: " + maker_o.dex.order[2] + " status: " + dx_refresh['status'] + \
              " time_to_execute (s):", time.time() - timer_lenght
    print(message)
    taker_logger.critical(message)
    return dx_done


def cex_check_inprogress_order(cex_order, ccxt_o):
    done = 0
    timer_lenght = time.time()
    count = 0
    order_refresh = 0
    while done == 0:
        order_refresh = ccxt.ccxt_call_fetch_order(cex_order['id'], ccxt_o)
        count += 1
        if count % 5 == 0:
            print("CEX order:\n", order_refresh)
        if 'status' in order_refresh:
            if 'closed' in order_refresh['status']:
                done = 1
            elif 'canceled' in order_refresh['status'] or 'expired' in order_refresh['status']:
                done = -1
        time.sleep(2)
    print(order_refresh)
    taker_logger.critical(order_refresh)
    return done


def execute_trade(maker_o, taker_o, ccxt_o):
    from_add = ""
    to_add = ""
    if "BUY" in maker_o.dex.side:
        from_add = taker_o.dex.active_address
        to_add = maker_o.dex.active_address
    if "SELL" in maker_o.dex.side:
        from_add = maker_o.dex.active_address
        to_add = taker_o.dex.active_address
    if not settings.dry_mode:
        mess = "dxtakerorder(" + maker_o.dex.order[2] + ", " + from_add + ', ' + to_add + ")"
        taker_logger.critical(mess)
        print(mess)
        xb.dx_call_takeorder(maker_o.dex.order[2], from_add, to_add)
        dx_done = dx_check_inprogress_order(maker_o)
        if dx_done == 1:
            if "SELL" in maker_o.cex.side_s1:
                new_price = maker_o.cex.final_price_cex_book_s1 * (1 - settings.error_rate_mod)
                maker_o.cex.final_price_cex_book_s1 = new_price
            elif "BUY" in maker_o.cex.side_s1:
                new_price = maker_o.cex.final_price_cex_book_s1 * (1 + settings.error_rate_mod)
                maker_o.cex.final_price_cex_book_s1 = new_price
            mess = 'ccxt_call_create_limit_order(' + maker_o.cex.side_s1 + ', ' + maker_o.cex.symbol_s1 + ', ' + str(
                maker_o.dex.maker_amount) + ', ' + str(
                maker_o.cex.final_price_cex_book_s1) + ', ccxt_o), dry_mode: ' + str(settings.dry_mode)
            taker_logger.critical(mess)
            print(mess)
            s1_cex_order = ccxt.ccxt_call_create_limit_order(maker_o.cex.side_s1, maker_o.cex.symbol_s1,
                                                             maker_o.dex.maker_amount,
                                                             maker_o.cex.final_price_cex_book_s1,
                                                             ccxt_o)
            cex_s1_done = cex_check_inprogress_order(s1_cex_order, ccxt_o)
            if cex_s1_done == 1 and not maker_o.cex.symbol_s2:
                return True
            if cex_s1_done == 1 and maker_o.cex.symbol_s2:
                if "SELL" in maker_o.cex.side_s2:
                    new_price = maker_o.cex.final_price_cex_book_s2 * (1 - settings.error_rate_mod)
                    maker_o.cex.final_price_cex_book_s2 = new_price
                elif "BUY" in maker_o.cex.side_s2:
                    new_price = maker_o.cex.final_price_cex_book_s2 * (1 + settings.error_rate_mod)
                    maker_o.cex.final_price_cex_book_s2 = new_price
                mess = 'ccxt_call_create_limit_order(' + maker_o.cex.side_s2 + ', ' + maker_o.cex.symbol_s2 + ', ' + \
                       str(maker_o.dex.taker_amount) + ', ' + str(maker_o.cex.final_price_cex_book_s2) + \
                       ', ccxt_o), dry_mode: ' + str(settings.dry_mode)
                taker_logger.critical(mess)
                print(mess)
                s2_cex_order = ccxt.ccxt_call_create_limit_order(maker_o.cex.side_s2, maker_o.cex.symbol_s2,
                                                                 maker_o.dex.taker_amount,
                                                                 maker_o.cex.final_price_cex_book_s2,
                                                                 ccxt_o)
                cex_s2_done = cex_check_inprogress_order(s2_cex_order, ccxt_o)
                if cex_s2_done == 1:
                    return True
                else:
                    print("error with CEX S2")
                    exit()
            else:
                print("error with CEX S1")
                exit()
        elif dx_done == -2:
            maker_o.dex.order_blacklist.append(maker_o.dex.order[2])
            mess = "error with DX, order was still 'open' after taking it, cancelling CEX execution \nblacklist " + \
                   maker_o.dex.order[2]
            print(mess)
            taker_logger.critical(mess)
            return False
        else:
            print("error with DX, cancelling CEX execution")
            exit()
    else:
        # DRY MODE
        mess3 = ""
        mess1 = "dxtakerorder(" + maker_o.dex.order[2] + ", " + from_add + ", " + to_add + "), dry_mode: " + str(
            settings.dry_mode)
        print(mess1)
        if "SELL" in maker_o.cex.side_s1:
            new_price = maker_o.cex.final_price_cex_book_s1 * (1 - settings.error_rate_mod)
            print(maker_o.cex.final_price_cex_book_s1, new_price)
            maker_o.cex.final_price_cex_book_s1 = new_price
        elif "BUY" in maker_o.cex.side_s1:
            new_price = maker_o.cex.final_price_cex_book_s1 * (1 + settings.error_rate_mod)
            print(maker_o.cex.final_price_cex_book_s1, new_price)
            maker_o.cex.final_price_cex_book_s1 = new_price
        mess2 = 'ccxt_call_create_limit_order(' + maker_o.cex.side_s1 + ', ' + maker_o.cex.symbol_s1 + ', ' + str(
            maker_o.dex.maker_amount) + ', ' + str(
            maker_o.cex.final_price_cex_book_s1) + ', ccxt_o), dry_mode: ' + str(settings.dry_mode)
        print(mess2)
        if maker_o.cex.symbol_s2:
            if "SELL" in maker_o.cex.side_s2:
                new_price = maker_o.cex.final_price_cex_book_s2 * (1 - settings.error_rate_mod)
                print(maker_o.cex.final_price_cex_book_s2, new_price)
                maker_o.cex.final_price_cex_book_s2 = new_price
            elif "BUY" in maker_o.cex.side_s2:
                new_price = maker_o.cex.final_price_cex_book_s2 * (1 + settings.error_rate_mod)
                print(maker_o.cex.final_price_cex_book_s2, new_price)
                maker_o.cex.final_price_cex_book_s2 = new_price
            mess3 = 'ccxt_call_create_limit_order(' + maker_o.cex.side_s2 + ', ' + maker_o.cex.symbol_s2 + ', ' + str(
                maker_o.dex.taker_amount) + ', ' + str(
                maker_o.cex.final_price_cex_book_s2) + ', ccxt_o), dry_mode: ' + str(
                settings.dry_mode)
            print(mess3)
        if maker_o.cex.symbol_s2:
            taker_logger.critical(
                "ARB ACTION:\n" + mess1 + "\n" + mess2 + "\n" + mess3)
        else:
            taker_logger.critical("ARB ACTION:\n" + mess1 + "\n" + mess2)
        maker_o.dex.order_blacklist.append(maker_o.dex.order[2])


def print_balances(coins_list, count):
    bal_msg = f"{'COIN_NAME':<10}| {'DEX_BAL':<14}| {'CEX_BAL':<14}| {'PANG_BAL':<14}| {'TOTAL_BAL':<14}"
    print(bal_msg)
    array = [["COIN_NAME", "DEX_BAL", "CEX_BAL", "PANG_BAL", "TOTAL_BAL"]]
    print("____________________________________________________")
    for coin in coins_list:
        bal_msg = f"{coin.name:<10}| {'{:.6f}'.format(coin.dex.balance):<14}| {'{:.8f}'.format(coin.cex.balance):<14}| {'{:.8f}'.format(coin.amm.balance):<14}| {'{:.8f}'.format(coin.dex.balance + coin.cex.balance + coin.amm.balance):<14}"
        print(bal_msg)
        array.append([coin.name, coin.dex.balance, coin.cex.balance, coin.amm.balance, coin.dex.balance + coin.cex.balance + coin.amm.balance])
    if count % 5 == 0:
        taker_balance_logger.info(array)


def reset_order_side(maker_o, taker_o):
    maker_o.dex.reset_order()
    taker_o.dex.reset_order()
    maker_o.cex.reset_side()
    taker_o.cex.reset_side()


def main_arb_taker_dx_ccxt():
    count = 0
    flush_cancelled_delay = 60 * 15
    flush_cancelled_timer = time.time()
    xb.dx_call_dxflushcancelledorders()
    ccxt_cex = ccxt.init_ccxt_instance(exchange=settings.ccxt_exchange_name, hostname=settings.ccxt_exchange_hostname)
    coins_list = main_init_coins_list()
    dx_set_addresses(coins_list)
    if settings.pangolin_enabled:
        pangolin_dx = Pangolin(settings.operator_address, settings.private_key, settings.provider, version=2, max_slippage='0.1')
    while 1:
        if time.time() - flush_cancelled_timer > flush_cancelled_delay:
            xb.dx_call_dxflushcancelledorders()
            flush_cancelled_timer = time.time()
        count += 1
        # GET BALANCES DX
        update_balances_dx(coins_list)
        # GET BALANCES CEX
        update_balances_cex(coins_list, ccxt_cex)
        if settings.pangolin_enabled:
            update_balance_pang(coins_list, pangolin_dx)
        # print("COIN_NAME, DEX_BAL, CEX_BAL")
        print_balances(coins_list, count)
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        main_timer = time.time()
        # GET ACTIVE ORDERBOOKS DX
        active_dx_markets = dx_get_active_dx_markets(coins_list)
        # COMPARE TO CEX BOOKS / CONVERT RATES
        for dx_market in active_dx_markets:
            maker_o = next(x for x in coins_list if x.name == dx_market['maker'])
            taker_o = next(x for x in coins_list if x.name == dx_market['taker'])
            reset_order_side(maker_o, taker_o)
            maker_o.dx_update_orderbook(taker_o)
            if "BTC" in maker_o.name or "BTC" in taker_o.name:
                # CALC ARB ONE HOP "BTC"
                if calc_arb_direct(maker_o, taker_o, coins_list, ccxt_cex) is True:
                    # EXECUTE DEX/CEX IF PROFITABLE TRADE FOUND // BALANCES CHECKS OK
                    if execute_trade(maker_o, taker_o, ccxt_o=ccxt_cex) is True:
                        print("SUCCESS!")
                        time.sleep(5)
            else:
                # CALC ARB 2 HOP COIN2 TO "BTC"
                if calc_arb_triway(maker_o, taker_o, coins_list, ccxt_cex) is True:
                    # EXECUTE DEX/CEX IF PROFITABLE TRADE FOUND // BALANCES CHECKS OK
                    if execute_trade(maker_o, taker_o, ccxt_o=ccxt_cex) is True:
                        print("SUCCESS!")
                        time.sleep(5)
            print()
        while time.time() - main_timer < settings.time_per_loop:
            print("*", end='')
            time.sleep(1)
        print("*")
