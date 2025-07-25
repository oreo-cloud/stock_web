from flask import Flask, render_template, request, Response, jsonify
import pandas as pd
import requests
import json
import io
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import pytz
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from collections import Counter

load_dotenv()  # 這行要在你讀 os.environ 之前

app = Flask(__name__)

uri = os.getenv('mongo_url')
client = MongoClient(uri, server_api=ServerApi('1'))

def get_yesterday_str():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tz)
    yest = now - timedelta(days=1)
    return yest.strftime('%Y%m%d')

def get_last_year_str():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tz)
    if now.month < 6:
        last_year = now.year - 2
    else:
        last_year = now.year - 1
    return str(last_year)

from collections import Counter
from datetime import datetime
import requests

def get_dividend_info(stock_code):
    last_year = get_last_year_str()
    url = 'https://api.finmindtrade.com/api/v4/data'
    params = {
        'dataset': 'TaiwanStockDividend',
        'data_id': stock_code,
        'start_date': f'{last_year}-01-01',
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    dividend_list = data.get('data', [])

    if not dividend_list:
        return {
            'msg': f'查無 {stock_code} 配息資料',
            'main_months': [],
            'occasional_months': [],
            'raw_counter': {},
            'latest_dividend': None
        }

    # 統計配息月份
    payment_dates = [x['CashDividendPaymentDate'] for x in dividend_list if x.get('CashDividendPaymentDate')]
    payment_dates = [d for d in payment_dates if d]
    payment_dates = sorted(list(set(payment_dates)), reverse=True)

    months_list = [int(d.split('-')[1]) for d in payment_dates]
    counter = Counter(months_list)
    total = sum(counter.values())
    main_months = [m for m, c in counter.items() if c / total >= 0.3]
    occasional_months = [m for m in counter if m not in main_months]

    # 取最新一筆現金股利（用發放日排序）
    latest_dividend = None
    if payment_dates:
        latest_date = payment_dates[0]
        for x in dividend_list:
            if x.get('CashDividendPaymentDate') == latest_date:
                cash_dividend = x['CashEarningsDistribution']
                ex_div_date = x['CashExDividendTradingDate']

                # 取得除息日的收盤價
                close_price = None
                dividend_yield = None
                if ex_div_date:
                    price_params = {
                        'dataset': 'TaiwanStockPrice',
                        'data_id': stock_code,
                        'start_date': ex_div_date,
                        'end_date': ex_div_date,
                    }
                    price_resp = requests.get(url, params=price_params)
                    price_data = price_resp.json().get('data', [])
                    if price_data:
                        close_price = price_data[0]['close']
                        try:
                            if close_price and cash_dividend:
                                dividend_yield = round(float(cash_dividend) / float(close_price) * 100, 2)
                        except Exception as e:
                            dividend_yield = None

                latest_dividend = {
                    '發放日': x['CashDividendPaymentDate'],
                    '除息日': ex_div_date,
                    '現金股利': cash_dividend,
                    '除息日收盤價': close_price,
                    '殖利率(%)': dividend_yield
                }
                break

    return {
        'main_months': sorted(main_months),
        'occasional_months': sorted(occasional_months),
        'raw_counter': dict(counter),
        'latest_dividend': latest_dividend
    }


def fetch_twse_daily():
    db = client['stockdb']
    col = db['twse_stocks']

    # 先查 MongoDB
    count = col.count_documents({})
    if count > 0:
        # 已有資料，直接回傳 DataFrame
        data = list(col.find({}, {"_id": 0, "證券代號": 1, "證券名稱": 1}))
        return pd.DataFrame(data)

    # 沒資料就抓
    date_str = get_yesterday_str()
    all_stocks_url_prefix = os.getenv('all_stocks_url_prefix')
    all_stocks_url_postfix = os.getenv('all_stocks_url_postfix')
    url = f"{all_stocks_url_prefix}{date_str}{all_stocks_url_postfix}"
    resp = requests.get(url)
    resp.encoding = 'big5'

    lines = resp.text.splitlines()
    idxs = []
    for i, line in enumerate(lines):
        if '證券代號' in line.replace('"', '').strip():
            idxs.append(i)
    if not idxs:
        raise Exception("找不到任何主要表格")

    dfs = []
    for block_no, start in enumerate(idxs):
        for j in range(start + 1, len(lines)):
            if not lines[j].strip():
                end = j
                break
        else:
            end = len(lines)
        csv_block = '\n'.join(lines[start:end])
        try:
            df = pd.read_csv(io.StringIO(csv_block), dtype=str)
            if set(['證券代號', '證券名稱']).issubset(df.columns):
                df['證券代號'] = (
                    df['證券代號'].astype(str)
                    .str.replace(r'^="?([A-Za-z0-9]+)"?$', r'\1', regex=True)
                    .str.strip()
                )
                df = df[df['證券代號'].str.isdigit()]
                dfs.append(df[['證券代號', '證券名稱']])
        except Exception as e:
            print(f"處理第 {block_no} 個區塊時發生錯誤: {e}")
            continue

    if not dfs:
        raise Exception("沒有任何有效表格")
    result = pd.concat(dfs, ignore_index=True)
    result = result.drop_duplicates().reset_index(drop=True)

    # 清除舊資料（或用 col.drop() 也可）
    col.delete_many({})
    # 批次寫入每一筆股票（dict）
    col.insert_many(result.to_dict(orient='records'))

    return result

def parse_stock_data(data):
    if not data or 'msgArray' not in data or not data['msgArray']:
        return None

    msg = data['msgArray'][0]
    return msg['z']

def get_stock_info(code):
    # tse or otc .tw
    url = os.getenv('stock_URL')
    testing_url = f"{url}tse_{code}.tw"
    try:
        resp = requests.get(testing_url)
        resp.encoding = 'utf-8'
        data = resp.json()
    except Exception as e:
        print(f"抓取 {testing_url} 時發生錯誤: {e}")
        testing_url = f"{url}otc_{code}.tw"
        try:
            resp = requests.get(testing_url)
            resp.encoding = 'big5'
            data = resp.json()
        except Exception as e:
            print(f"抓取 {testing_url} 時發生錯誤: {e}")
            return None
    
    data = parse_stock_data(data)

    return data
    
@app.route('/search_stocks', methods=['GET'])
def search_stocks():
    q = request.args.get('q', '').strip()
    df = fetch_twse_daily()
    # 只保留純數字代號
    df = df[df['證券代號'].str.isdigit()]
    if q:
        # 模糊搜尋（證券代號或名稱）
        df = df[df['證券代號'].str.contains(q) | df['證券名稱'].str.contains(q)]
    # 最多回傳前 30 筆
    df = df.head(30)
    # 處理 NaN
    df = df.where(pd.notnull(df), None)
    json_str = json.dumps(df.to_dict(orient='records'), ensure_ascii=False)
    return Response(json_str, content_type='application/json; charset=utf-8')

@app.route('/get_stocks_names', methods=['GET'])
def get_stocks_names():
    df = fetch_twse_daily()
    # 注意 ensure_ascii=False
    json_str = json.dumps(df.to_dict(orient='records'), ensure_ascii=False)
    return Response(json_str, content_type='application/json; charset=utf-8')

@app.route('/add_stock', methods=['POST'])
def add_stock():
    data = request.get_json()
    if not data or '證券代號' not in data:
        return jsonify({'status': 'error', 'message': '缺少必要的參數'}), 400
    db = client['user']
    col = db['stocks']
    col.update_one(
        {'user': "X", '證券代號': data['證券代號']},
        {'$set': {
            '證券代號': data['證券代號'],
            '證券名稱': data['證券名稱'],
            'user': "X"
        }},
        upsert=True
    )
    
    return jsonify({'status': 'ok'})

@app.route('/remove_stock', methods=['POST'])
def remove_stock():
    data = request.get_json()
    if not data or '證券代號' not in data:
        return jsonify({'status': 'error', 'message': '缺少必要的參數'}), 400
    db = client['user']
    col = db['stocks']
    result = col.delete_one({'user': "X", '證券代號': data['證券代號']})
    if result.deleted_count == 0:
        return jsonify({'status': 'error', 'message': '股票代號不存在'}), 404
    return jsonify({'status': 'ok'})

@app.route('/get_user_stocks', methods=['GET'])
def get_user_stocks():
    db = client['user']
    col = db['stocks']
    user_stocks = list(col.find({'user': "X"}, {'_id': 0, 'user': 0}))
    user_stocks.sort(key=lambda x: x['證券代號'])  # 按證券代號排序
    return jsonify(user_stocks)

@app.route('/get_dividend_info', methods=['GET'])
def get_dividend_info_api():
    code = request.args.get('code')
    stock_transaction_price = get_stock_info(code) # 成交價 (num)
    info = get_dividend_info(code) # 配息月份 (list) + 最新股利 (dict) + 殖利率

    latest_dividend = info['latest_dividend'] or {}

    return jsonify({
        'stock_transaction_price': stock_transaction_price, # 成交價
        'Payment_cycle': info.get('main_months', []),               # 配息月份
        'dividend': latest_dividend.get("現金股利"),     # 最新股利
        'yield': latest_dividend.get("殖利率(%)")        # 殖利率
    })

@app.route('/')
def home():
    # 回傳 templates/index.html
    return render_template('index.html')

if __name__ == '__main__':
    app.run()
