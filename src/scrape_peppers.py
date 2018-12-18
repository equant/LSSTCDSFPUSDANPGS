import sys
from time import sleep
from random import randint
import requests
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd

raw_html = open('capsicum_accessions.html').read()
html = BeautifulSoup(raw_html, 'html.parser')

foo = html.select('a')
foo = [x for x in foo if "href" in x.attrs.keys()]
foo = [x for x in foo if "accessiondetail" in x.attrs['href']]

data = [(x.attrs['href'], x.string) for x in foo]

from random import shuffle
shuffle(data)

TESTING = False
if TESTING:
    #my_test_url = 'https://npgsweb.ars-grin.gov/gringlobal/accessiondetail.aspx?id=1047133'
    #data = np.array(data)
    #_idx = np.where(data[:,0] == my_test_url)
    #data = data[_idx]
    data = data[:10]

df = pd.DataFrame(data, columns=['url', 'plant_id'])
df['id'] = [int(x.split('?')[-1].split("=")[-1]) for x in df['url']] 
df = df.set_index('id')
df_full = df.copy()


from cachecontrol import CacheControl
sess = requests.session()
cached_sess = CacheControl(sess)

bad_responses = []
count = 0
for plant_id, row in df.iterrows():
    print(plant_id)
    url = row['url']

    response = cached_sess.get(url)
    if response.status_code != 200:
        print(f"Boo")
        bad_responses.append(url)
        df_full.loc[plant_id, 'error'] = 'url'
        continue

    try:
        html = BeautifulSoup(response.content, 'html.parser')
        tables = html.select('table')
        evaluation_table = tables[-2]
        #column_names = evaluation_table.select("tr")[1].select("th")[1:]
        #column_names = [x.string for x in column_names]
        all_values       = evaluation_table.select("tr")[2].select("td")
        all_values       = [x.string for x in all_values]


        column_table_headers = evaluation_table.select("tr")[1].select("th")[1:]
        saved_values = []
        column_names = []
        col_count    = 0
        for _c_idx, th in enumerate(column_table_headers):
            n_colspan = int(th.attrs['colspan'])
            column_name = th.string
            column_names.append(column_name)
            col_count += n_colspan - 1
            value = all_values[col_count]
            saved_values.append(value)
            print(f"{_c_idx:6} - {col_count} - {column_name:20} {value:20}")
            col_count += 1
        values = saved_values

    except IndexError:
        print(f"No features for this accession")
        df_full.loc[plant_id, 'error'] = 'no features'
        continue

    try:
        location_row = tables[34].select("tr")[0]
        if location_row.select("th")[0].string == 'Collected from:':
            loc = location_row.select("td")[0].string.strip()
            if len(log) > 0:
                values.append(loc)
                column_names.append('scraped_location')
    except:
        pass
    
    latin_name = html.select('h2')[0].select('a')[0].string.strip()
    df.loc[plant_id, 'latin_name'] = latin_name
    df_full.loc[plant_id, 'latin_name'] = latin_name

    for column_idx, column in enumerate(column_names):
        column = column.lower()
        value_full = values[column_idx]
        df_full.loc[plant_id, column] = value_full
        if (value_full != '0 - ABSENT'):
            try:
                value_short = value_full.split("-")[0]
                value_short = float(value_short)
                df.loc[plant_id, column] = value_short
            except:
                print(f"Was not able to save {value_full} as a short value")

    count += 1
    print(f"Sleep... {count}/{len(df)}")
    sleep(randint(3,7))

df.to_csv(f"capsicum_ml_{len(df)}.csv")
df_full.to_csv(f"capsicum_full_{len(df_full)}.csv")

#for url, acc_id in data[:1]:

