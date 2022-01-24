#!/usr/bin/python3
from utils.authproxy import AuthServiceProxy
import flask.json
import decimal
import time
import calendar
import dateutil
from dateutil import parser
import arbtaker_settings

rpc_connection = AuthServiceProxy(
    "http://%s:%s@127.0.0.1:%s" % (
    arbtaker_settings.rpc_user, arbtaker_settings.rpc_password, arbtaker_settings.rpc_port))


class MyJSONEncoder(flask.json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            # convert decimal instances to strings
            return str(obj)
        return super(MyJSONEncoder, self).default(obj)


def lookup_order_id(orderid, myorders):
    # find my orders, returns order if orderid passed is inside myorders
    return [zz for zz in myorders if zz['id'] == orderid]


def get_market_pair_history(coin1, coin2, start, end, granularity, guid):
    result = rpc_connection.dxGetOrderHistory(coin1, coin2, start, end, granularity, guid)
    return result


def canceloldestorder(maker, taker):
    myorders = getopenordersbymarket(maker, taker)
    oldestepoch = 3539451969
    currentepoch = 0
    epochlist = 0
    oldestorderid = 0
    for z in myorders:
        if z['status'] == "open":
            createdat = z['created_at']
            currentepoch = getepochtime((z['created_at']))
            if oldestepoch > currentepoch:
                oldestorderid = z['id']
                oldestepoch = currentepoch
            if oldestorderid != 0:
                rpc_connection.dxCancelOrder(oldestorderid)
    return oldestorderid, oldestepoch


def cancelorder(order_id):
    result = rpc_connection.dxCancelOrder(order_id)
    return result


def getnewtokenadress(token):
    result = rpc_connection.dxGetNewTokenAddress(token)
    return result


def cancelallorders():
    # cancel all my open orders
    myorders = rpc_connection.dxGetMyOrders()
    for z in myorders:
        if z['status'] == "open" or z['status'] == "new":
            results = rpc_connection.dxCancelOrder(z['id'])
            time.sleep(1)
            print(results)
    return


def getmyopenorders(coin1, coin2):
    myorders = rpc_connection.dxGetMyOrders()
    result = []
    for order in myorders:
        if (order['status'] == "open" or order['status'] == 'new') and (
                (order['maker'] == coin1 and order['taker'] == coin2) or (
                order['maker'] == coin2 and order['taker'] == coin1)):
            result.append(order)
    return result


def cancelallordersbymarket(maker, taker):
    # cancel all my open orders
    myorders = getopenordersbymarket(maker, taker)
    for z in myorders:
        if z['status'] == "open" or z["status"] == "new":
            results = rpc_connection.dxCancelOrder(z['id'])
            time.sleep(3.5)
            print(results)
    return


def getmyordersbymarket(maker, taker):
    # returns open orders by market
    myorders = rpc_connection.dxGetMyOrders()
    return [zz for zz in myorders if (zz['maker'] == maker) and (zz['taker'] == taker)]


def getopenordersbymarket(maker, taker):
    # returns open orders by market
    myorders = rpc_connection.dxGetMyOrders()
    return [zz for zz in myorders if
            (zz['status'] == "open" or zz['status'] == "new") and (zz['maker'] == maker) and (zz['taker'] == taker)]


def getopenordersbymaker(maker):
    # return orders open w/ maker 
    myorders = rpc_connection.dxGetMyOrders()
    return [zz for zz in myorders if (zz['status'] == "open" or zz['status'] == "open") and (zz['maker'] == maker)]


def getopenorders():
    # return open orders
    myorders = rpc_connection.dxGetMyOrders()
    return [zz for zz in myorders if (zz['status'] == "open" or zz['status'] == "new")]


def getopenorder_ids():
    # return open order IDs
    myorders = rpc_connection.dxGetMyOrders()
    return [zz['id'] for zz in myorders if (zz['status'] == "open" or zz['status'] == "new")]


def getepochtime(created):
    # converts created to epoch
    return calendar.timegm(dateutil.parser.parse(created).timetuple())


def getorderbook(maker, taker):
    fullbook = rpc_connection.dxGetOrderBook(3, maker, taker)
    # print(fullbook)
    asklist = fullbook['asks']
    bidlist = fullbook['bids']
    return (asklist, bidlist)


def getlowprice(orderlist):
    return min(orderlist, key=lambda x: x[0])


def gethighprice(orderlist):
    return max(orderlist, key=lambda x: x[0])


def makeorder(maker, makeramount, makeraddress, taker, takeramount, takeraddress):
    #
    results = rpc_connection.dxMakeOrder(maker, makeramount, makeraddress, taker, takeramount, takeraddress, 'exact')
    if 'id' in results:
        return results
    else:
        raise RuntimeError(results)


def takeorder(id, fromaddr, toaddr):
    results = rpc_connection.dxTakeOrder(id, fromaddr, toaddr)
    return results


# return float balance of specific token or return 0 of not exist
def get_token_balance(balances, token_name):
    return float(balances.get(token_name, 0))


def getorderstatus(id):
    result = rpc_connection.dxGetOrder(id)
    return result


def showorders():
    print('### Getting balances >>>')
    mybalances = rpc_connection.dxGetTokenBalances()
    print(mybalances)
    print('### Getting my orders >>>')
    myorders = rpc_connection.dxGetMyOrders()
    for z in myorders:
        print(z['status'], z['id'], z['maker'], z['maker_size'], z['taker'], z['taker_size'],
              float(z['taker_size']) / float(z['maker_size']))

    allorders = rpc_connection.dxGetOrders()
    print('#############################################################')
    for z in allorders:
        # checks if your order
        if lookup_order_id(z['id'], myorders):
            ismyorder = "True"
        else:
            ismyorder = "False"
