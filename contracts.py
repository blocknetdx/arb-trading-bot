import json
from web3 import Web3


pangRouterContract = Web3.toChecksumAddress("0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106")

wavaxContract = Web3.toChecksumAddress("0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7")
aablockContract = Web3.toChecksumAddress("0xc931f61b1534eb21d8c11b24f3f5ab2471d4ab50")
usdtContract = Web3.toChecksumAddress("0xc7198437980c041c805a1edcba50c1ce5db95118")
pangolinContract = Web3.toChecksumAddress("0x60781c2586d68229fde47564546784ab3faca982")

with open("abi/pang.json") as pangFile:
    pangRouter_abi = json.load(pangFile)

