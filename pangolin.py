from typing import List
import web3
from web3 import Web3
from contracts import pangRouterContract, pangRouter_abi


class Pangolin:

    def __init__(self, network: str):
        self.provider = Web3(Web3.HTTPProvider(network))
        self.pangRouter = self.provider.eth.contract(address=pangRouterContract,
                                                     abi=pangRouter_abi)

    def price(self,
              amount: float,
              token1: str,
              token2: str) -> List:
        """

        :param amount: Amount of input
        :param token1: contract address of token
        :param token2: contract address of token
        :return: the list of amount of output token per token
        """
        price = self.pangRouter.functions.getAmountsOut(amount, [token1, token2]).call()

        return price

    def swap(self,
             token1: str,
             token2: str,
             amount_token1: float,
             amount_token2: float,
             time: int,
             address: str) -> List:
        """

        :param token1:
        :param token2:
        :param amount_token1:
        :param amount_token2:
        :param time:
        :param address:
        :return:
        """
        tokens = self.pangRouter.functions.swapExactTokensForTokens(amount_token1,
                                                                    amount_token2,
                                                                    [token1, token2],
                                                                    address, time).call()

        return tokens

    def approve(self, token, private_key, wallet_address, spender_address):
        """
        :return:
        """
        spender = spender_address
        max_amount = web3.toWei(2 ** 64 - 1, 'ether')
        nonce = web3.eth.getTransactionCount(wallet_address)

        tx = token.functions.approve(spender, max_amount).buildTransaction({
            'from': wallet_address,
            'nonce': nonce
        })

        signed_tx = web3.eth.account.signTransaction(tx, private_key)
        tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)

        return web3.toHex(tx_hash)
