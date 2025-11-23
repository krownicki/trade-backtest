# ogólny skrypt aby pobierać dane dla
# start_timestamp
# end_timestamp
# symbol_id
# period
# i zapisywać jako CSV
import logging

import requests
import datetime
from datetime import timezone

url = "http://localhost:9000"

def fetch_prices(start_date, end_date, symbol_id, period, filename=None):
    health = requests.get(f"{url}/connection").json()
    if health['authenticated'] and not health['connected']:
        account_id = 24969777
        res = connect_to_account(account_id)
        if not res:
            logging.error(f"Cannot connect to the account {account_id}")
            return
    body = {"symbol_id": symbol_id, "start_time": dt_to_string(start_date), "end_time": dt_to_string(end_date), "period": period}
    start_export_json = requests.post(f"{url}/trendbars/export", json=body).json()
    status = requests.get(f"{url}/trendbars/export/{start_export_json['export_id']}/status").json()
    if status['status'] == 'ready':
        logging.info("Fetching csv file")
        res = requests.get(f"{url}/trendbars/export/{status['export_id']}/download")
        filename = f"{status['export_id']}.csv" if not filename else filename
        with open(filename, "wb") as f:
            f.write(res.content)


def connect_to_account(account_id):
    accounts = requests.get(f"{url}/auth/accounts").json()
    if account_id in [x['ctidTraderAccountId'] for x in accounts]:
        acc = requests.get(f"{url}/auth/connect/{account_id}").json()
        logging.info(f"Connecting to {account_id}, status: {acc['status']}")
        return acc['status']
    return False

def dt_to_string(dt: datetime) -> str:
    # zapewnienie strefy UTC
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

# if __name__ == "__main__":
#     start_date = datetime.datetime(2025, 10, 1)
#     end_date = datetime.datetime(2025, 11, 23)
#     symbol_id = 10019
#     period = 1
    fetch_prices(start_date, end_date, symbol_id, period)