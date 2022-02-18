# Arb bot

`pip3 install -r requirements.txt`

open arbtaker_settings.py with text editor:

-Set correct `rpc_user`, `rpc_password`, `rpc_port`, corresponding to your blocknet core wallet.

-`dry_mode` to `True` won't execute trade in real, just execute logic and console/logging.

-`dry_mode` to `False` will execute trade in real.

-Set `pangolin_enabled` to `True` will enable pangoling exchange

-`operator_address`, `private_key`, corresponding to your avalanche wallet

-Bot will gather new xbridge addresses at first run.


open `utils/keys.local.json` with text editor:

-Set your active ccxt exchange name / api_key / api_secret

open `utils/contracts.py`

-Add desired token addresess from pangolin exchange

start:
`python3 main.py`

