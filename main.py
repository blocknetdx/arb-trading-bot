from pangolin import Pangolin
from contracts import (aablockContract,
                       usdtContract)
from web3 import Web3, types
import configfile


my_address = "0xa3786dd1e130197EA72042b8821207e20aeFeD90"
my_pk = "0000000000000000000000000000000000000000000000000000000000000000"

provider = "https://api.avax.network/ext/bc/C/rpc"

pang = Pangolin(my_address, my_pk, provider, version=2, max_slippage='0.03')

price = pang.get_token_token_input_price(usdtContract, aablockContract, 1)
print(price/100)


gwei = types.Wei(Web3.toWei(int(configfile.maxgweinumber), "gwei"))


pang.make_trade(aablockContract, usdtContract, 1, gwei, my_address, my_pk)
