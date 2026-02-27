import os
from dotenv import load_dotenv

from py_clob_client.client import ClobClient


def main():
    load_dotenv()

    host = os.getenv("CLOB_HOST", "https://clob.polymarket.com")
    chain_id = int(os.getenv("CHAIN_ID", "137"))
    private_key = os.getenv("PRIVATE_KEY")
    signature_type = int(os.getenv("SIGNATURE_TYPE", "0"))
    funder = os.getenv("FUNDER")

    if not private_key:
        raise RuntimeError("Missing PRIVATE_KEY in .env")
    if not funder:
        raise RuntimeError("Missing FUNDER in .env")

    # Derive API creds
    temp_client = ClobClient(host, key=private_key, chain_id=chain_id)
    api_creds = temp_client.create_or_derive_api_creds()

    # Authenticated client
    client = ClobClient(
        host,
        key=private_key,
        chain_id=chain_id,
        creds=api_creds,
        signature_type=signature_type,
        funder=funder,
    )

    # Safe read-only checks
    balances = client.get_balance_allowance(params={"asset_type": "COLLATERAL"})
    open_orders = client.get_orders()

    print("SDK auth check passed")
    print(f"Signature type: {signature_type}")
    print(f"Funder: {funder}")
    print(f"Open orders: {len(open_orders) if isinstance(open_orders, list) else 'ok'}")
    print("Collateral allowance/balance response:")
    print(balances)


if __name__ == "__main__":
    main()
