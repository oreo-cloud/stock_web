import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
import urllib3

# 關掉警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_twse_isin(url):
    resp = requests.get(url, verify=False)
    resp.encoding = 'big5'
    soup = BeautifulSoup(resp.text, 'html.parser')
    tables = soup.find_all('table')
    # 有時 tables[1] 才是你要的資料
    for i, t in enumerate(tables):
        if '有價證券代號' in t.text:  # 用關鍵字判斷
            target_table = t
            print(f"用第 {i} 個 table")
            break
    else:
        raise Exception('找不到正確的 table')
    df = pd.read_html(StringIO(str(target_table)))[0]
    # 去掉前兩行標題
    df = df.drop([0, 1]).reset_index(drop=True)
    df.columns = [
        '有價證券代號及名稱', '國際證券辨識號碼(ISIN Code)', '上市日', '市場別', '產業別', 'CFICode', '備註'
    ]
    return df

url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
df = fetch_twse_isin(url)
print(df.head())
