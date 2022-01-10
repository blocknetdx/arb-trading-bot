from web3 import Web3
from pangolin import Pangolin
from contracts import (
        aablockContract,
        wavaxContract,
        usdtContract,
        pangolinContract)


def main():

    pang = Pangolin('https://api.avax.network/ext/bc/C/rpc')
    price_wavax_aablock = pang.price(1, aablockContract, wavaxContract)
    price_wavax_usdt = pang.price(1, usdtContract, wavaxContract)
    aablock = 1/(price_wavax_aablock[1]/10**10)
    usdt = 1/(price_wavax_usdt[1]/10**12)

    print(aablock, 'aablock per wawax')
    print(usdt, 'usdt per wavax')
    print(aablock/usdt, 'aablock per usdt')

    try:
        pang.swap(aablockContract, wavaxContract, 1, 160,
                  1642327952, Web3.toChecksumAddress("0xffc53c9d889b4c0bfc1ba7b9e253c615300d9ffd"))
    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
