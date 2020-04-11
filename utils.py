import urllib.request
import requests
import json
import pandas as pd 
import datetime
import numpy as np

def get_data(url):
    req = urllib.request.Request(url)
    req.add_header('Accept', f"application/json")
    response = urllib.request.urlopen(req).read()

    result = json.loads(response)
    return result



import concurrent.futures

# Retrieve a single page and report the URL and contents
def get_one_month_asset(real_asset_id, year, month, day):
    print(f'requesting {year}, {str(month).zfill(2)}\t')
    return get_data(
        f"https://fintual.cl/api/real_assets/{real_asset_id}/days?date={year}%2F{str(month).zfill(2)}%2F{str(day).zfill(2)}"
    )

# Fintual
def get_monthly_assets(real_asset_id, from_year, from_month, to_year, to_month, day=1, debug=False):
    from_number = from_year * 12 + from_month - 1
    to_number = to_year * 12 + to_month - 1
    
    results = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_date = {
            executor.submit(get_one_month_asset, real_asset_id, int(month / 12), month % 12 + 1, day): [
                int(month / 12),
                month % 12 + 1,
            ]
            for month in range(from_number, to_number + 1)
        }
        for future in concurrent.futures.as_completed(future_to_date):
            date = future_to_date[future]
            if debug:
                print(f'got {date}')
            try:
                data = future.result()
                results.append(data)
            except Exception as exc:
                print("%r generated an exception: %s" % (date, exc))

    results = [s['data'][0]['attributes'] for s in results if len(s['data']) > 0]
    results.sort(key= lambda r : r['date'])
    return results

def get_daily_assets(real_asset_id, from_date, to_date):
    url = f"https://fintual.cl/api/real_assets/{real_asset_id}/days?to_date={to_date}&from_date={from_date}"
    response = requests.get(url)
    result = response.json()

    results_df = pd.DataFrame([a['attributes'] for a in result['data']])


    r = (results_df['price'].values[1:]/results_df['price'].values[:-1]) * 100
    r = np.hstack([r, [1]])
    results_df['ValorBase100'] = r
    results_df = results_df[:-1]
    results_df = results_df[['date', 'ValorBase100']]

    return results_df

# Confuturo

def make_confuturo_df(json_data):
    df = pd.DataFrame(json_data)
    df["timestamp"] = df["FechaUltima"].apply(
        lambda a: datetime.datetime.fromtimestamp(int(float(
            a.replace("/", "").replace("Date", "").replace("(", "").replace(")", "")
        )/1000))
    )
    return df[["timestamp", "ValorBase100"]]

def read_confuturo_dataframes():
    with open('./confuturo_1y_corporativo.json') as f:
        corporativo_data = json.loads(f.read())
        
    with open('./confuturo_1y_tecnologico.json') as f:
        tecnologico_data = json.loads(f.read())

    corporativo_df = make_confuturo_df(corporativo_data["Rentabilidades"])
    tecnologico_df = make_confuturo_df(tecnologico_data["Rentabilidades"])

    results_df = pd.concat([corporativo_df, tecnologico_df], keys=['corporativo', 'tecnologico'], names=['modalidad', 'Row ID'])
    return results_df, corporativo_df, tecnologico_df