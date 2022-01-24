from web3 import Web3


tokens = {
          'avax': 'wavax',
          'block': 'aablock',
          'usdt': 'usdt.e',
          'btc': 'wbtc.e'
        }

contracts = {}

contracts['wavax'] = Web3.toChecksumAddress("0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7")
contracts['aablock'] = Web3.toChecksumAddress("0xc931f61b1534eb21d8c11b24f3f5ab2471d4ab50")
contracts['usdt.e'] = Web3.toChecksumAddress("0xc7198437980c041c805a1edcba50c1ce5db95118")
contracts['wbtc.e'] = Web3.toChecksumAddress("0x50b7545627a5162f82a992c33b87adc75187b218")





