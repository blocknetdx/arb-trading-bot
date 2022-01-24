import json
import logging
import time

import definitions.logger as logger
import utils.dxbottools as dxbottools

dx_log = logger.setup_logger(name="XBRIDGE_LOG", log_file='logs/xbridge.log', level=logging.INFO)

dx_retry_timer = 1
debug = 0


def dx_manage_error(error, err_count=0, parent_func=""):
    import arbtaker_settings as settings
    max_fails = 30
    err_type = type(error).__name__
    err_str = str(error)[0:200].replace("'", '"')
    print("dx_manage_error, parent func = ", parent_func, ', [' + err_type + ']', err_str, err_count)
    dx_log.error(parent_func + '[' + err_type + ']: ' + err_str + ', err_count: ' + str(err_count))
    if settings.dry_mode:
        time.sleep(2 * err_count)
    else:
        if "RuntimeError" in err_type:
            err_dict = json.loads(err_str)
            if err_dict['code'] == 1026:
                print("err_dict['code'] == 1026, Wallet probably locked ?")
                if err_count >= max_fails:
                    print('reach err_count>=max_fails, exit')
                    exit()
            elif err_dict['code'] == 1032:
                print("err_dict['code'] == 1032, Unsupported asset error, blocknet wallet lost contact with network ?")
        elif "ConnectionResetError" in err_type:
            time.sleep(2 * err_count)
        elif "ConnectionRefusedError" in err_type:
            time.sleep(2 * err_count)
        elif "RemoteDisconnected" in err_type:
            time.sleep(2 * err_count)
        elif "timeout" in err_type:
            time.sleep(2 * err_count)
        elif "TypeError" in err_type or "KeyError" in err_type:
            time.sleep(2 * err_count)
            if err_count >= max_fails:
                print('reach err_count>=max_fails, exit')
                exit()
        elif "JSONRPCException" in err_type:
            if "-1: dxLoadXBridgeConf" in err_str:
                print("dxLoadXBridgeConf too fast, sleep", 5 * err_count, "s")
                time.sleep(5 * err_count)
            if err_count >= max_fails:
                print('reach err_count>=max_fails, exit')
                exit()
        else:
            print('unreferenced xbridge error, exit')
            exit()


def dx_call_dxgetlocaltokens():
    err_count = 0
    while True:
        try:
            result = dxbottools.rpc_connection.dxgetlocaltokens()
        except Exception as e:
            err_count += 1
            dx_manage_error(e, err_count=err_count, parent_func="dx_call_dxgetlocaltokens")
            time.sleep(err_count)
        else:
            return result


def dx_call_getnewtokenadress(coin):
    timer_perf = time.time()
    err_count = 0
    while True:
        try:
            result = dxbottools.getnewtokenadress(coin)
        except Exception as e:
            err_count += 1
            dx_manage_error(e, err_count=err_count, parent_func="dx_call_getnewtokenadress")
            time.sleep(err_count)
        else:
            if debug >= 2:
                print("dx_call_getnewtokenadress(" + coin + "), timer_perf: " + str(time.time() - timer_perf))
            return result


def dx_call_cancelorder(order_id):
    timer_perf = time.time()
    err_count = 0
    while True:
        try:
            result = dxbottools.cancelorder(order_id)
        except Exception as e:
            err_count += 1
            dx_manage_error(e, err_count=err_count, parent_func="dx_call_cancelorder")
            time.sleep(err_count)
        else:
            if debug >= 2:
                print("dx_call_cancelorder(", order_id, "), timer_perf: " + str(time.time() - timer_perf))
            return result


def dx_call_getorderbook(maker, taker, detail=1):
    timer_perf = time.time()
    err_count = 0
    while True:
        try:
            result = dxbottools.rpc_connection.dxgetorderbook(detail, maker, taker)
        except Exception as e:
            err_count += 1
            dx_manage_error(e, err_count=err_count, parent_func="dx_call_getorderbook")
            time.sleep(err_count)
        else:
            if debug >= 2:
                print("dx_call_getorderbook(", maker, taker, detail, "), timer_perf: " + str(time.time() - timer_perf))
            return result


def dx_call_getorderstatus(order_id):
    timer_perf = time.time()
    err_count = 0
    while True:
        try:
            result = dxbottools.getorderstatus(order_id)
        except Exception as e:
            err_count += 1
            dx_manage_error(e, err_count=err_count, parent_func="dx_call_getorderstatus")
            time.sleep(err_count)
        else:
            if debug >= 2:
                print("dx_call_getorderstatus(", order_id, "), timer_perf: " + str(time.time() - timer_perf))
            return result


def dx_call_dxflushcancelledorders(flushwindow=0):
    print("dx_call_dxflushcancelledorders")
    timer_perf = time.time()
    err_count = 0
    while True:
        try:
            result = dxbottools.rpc_connection.dxFlushCancelledOrders(flushwindow)
        except Exception as e:
            err_count += 1
            dx_manage_error(e, err_count=err_count, parent_func="dx_call_dxflushcancelledorders")
            time.sleep(err_count)
        else:
            if debug >= 2:
                print("dx_call_dxflushcancelledorders(", flushwindow, "), timer_perf: " + str(time.time() - timer_perf))
            return result


def dx_call_gettokensbalance() -> dict:
    timer_perf = time.time()
    err_count = 0
    while True:
        try:
            result = dxbottools.rpc_connection.dxGetTokenBalances()
        except Exception as e:
            err_count += 1
            dx_manage_error(e, err_count=err_count, parent_func="dx_call_gettokensbalance")
            time.sleep(err_count)
        else:
            if debug >= 2:
                print("dx_call_gettokensbalance(), timer_perf: " + str(time.time() - timer_perf))
            return result


def dx_call_takeorder(order_id, from_address, to_address):
    timer_perf = time.time()
    err_count = 0
    while True:
        try:
            result = dxbottools.takeorder(order_id, from_address, to_address)
        except Exception as e:
            err_count += 1
            dx_manage_error(e, err_count=err_count, parent_func="dx_call_makeorder")
            time.sleep(err_count)
        else:
            if debug >= 2:
                print("dx_call_makeorder(", order_id, from_address, to_address,
                      "), timer_perf: " + str(time.time() - timer_perf))
            return result
