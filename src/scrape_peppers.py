import sys
from time import sleep
from random import randint
import requests
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup

raw_html = open('capsicum_accessions.html').read()
html = BeautifulSoup(raw_html, 'html.parser')

foo = html.select('a')
foo = [x for x in foo if "href" in x.attrs.keys()]
foo = [x for x in foo if "accessiondetail" in x.attrs['href']]

data = [(x.attrs['href'], x.string) for x in foo]

import pandas as pd

TESTING = False
if TESTING:
    data = data[:5]

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
        column_names = evaluation_table.select("tr")[1].select("th")[1:]
        column_names = [x.string for x in column_names]
        values       = evaluation_table.select("tr")[2].select("td")
        values       = [x.string for x in values]
    except IndexError:
        print(f"No features for this accession")
        df_full.loc[plant_id, 'error'] = 'no features'
        continue
    
    latin_name = html.select('h2')[0].select('a')[0].string.strip()
    df.loc[plant_id, 'latin_name'] = latin_name
    df_full.loc[plant_id, 'latin_name'] = latin_name

    for column_idx, column in enumerate(column_names):
        column = column.lower()
        value_full = values[column_idx]
        df_full.loc[plant_id, column] = value_full
        if (value_full != '0 - ABSENT'):
            value_short = value_full[0]
            df.loc[plant_id, column] = value_short

    count += 1
    print(f"Sleep... {count}/{len(df)}")
    sleep(randint(2,7))

df.to_csv(f"capsicum_ml_{len(df)}.csv")
df_full.csv(f"capsicum_full_{len(df_full)}.csv")

#for url, acc_id in data[:1]:

