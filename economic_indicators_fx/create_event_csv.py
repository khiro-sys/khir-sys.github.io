import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime

# --- 設定項目 ---
# 情報を取得したいKissFXの週間スケジュールページのURL
# ここのURLを毎週書き換えて実行します
url = "https://kissfx.com/article/20240520weekfx.html" # 例: 2024年5月20日の週

# 出力するCSVファイル名 (EAのパラメータと合わせる)
output_csv_file = "economic_events.csv"
# ----------------

# 国名/地域名と3文字の通貨コードを対応付ける辞書
# KissFXのサイトで使われている国名に合わせています
currency_map = {
    "米国": "USD",
    "日本": "JPY",
    "ユーロ圏": "EUR",
    "英国": "GBP",
    "豪州": "AUD",
    "NZ": "NZD",
    "カナダ": "CAD",
    "スイス": "CHF",
    "中国": "CNY",
    # 必要に応じて他の国/通貨を追加
}

# 重要度（星の数）とEAで使う文字列を対応付ける辞書
impact_map = {
    3: "HIGH",
    2: "MEDIUM",
    1: "LOW"
}

def scrape_and_create_csv(target_url, output_file):
    """
    指定されたURLから経済指標をスクレイピングし、CSVファイルを作成する関数
    """
    print(f"'{target_url}' から情報を取得しています...")

    try:
        # 1. Webページの内容を取得
        response = requests.get(target_url)
        response.raise_for_status() # エラーがあれば例外を発生
        response.encoding = response.apparent_encoding # 文字化け防止

        # 2. HTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')

        # URLから年を取得 (例: "20240520" -> "2024")
        year_match = re.search(r'/(\d{8})weekfx', target_url)
        if not year_match:
            print("エラー: URLから年を特定できませんでした。")
            return
        year = year_match.group(1)[:4]

        # 3. 指標カレンダーのテーブルを特定
        # KissFXのテーブルには特定のIDやクラスがないため、ページ内の全てのテーブルを探す
        tables = soup.find_all('table')
        if not tables:
            print("エラー: ページ内にテーブルが見つかりませんでした。")
            return

        # 最初のテーブルが指標カレンダーだと仮定
        event_table = tables[0]
        
        # 抽出したデータを格納するリスト
        event_data = []

        # 4. テーブルの各行から情報を抽出
        for row in event_table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) < 4: # 必要な列がない行はスキップ
                continue

            # 各セルからテキスト情報を取得
            time_str = cols[0].get_text(strip=True)
            country_img = cols[1].find('img')
            country_name = country_img['alt'] if country_img else "不明"
            # 指標名は今回は使わない
            # event_name = cols[2].get_text(strip=True)
            impact_str = cols[3].get_text(strip=True)

            # --- 5. データの整形 ---
            # 日時を "YYYY.MM.DD HH:MM" 形式に変換
            match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', time_str)
            if not match:
                continue
            
            date_part = match.group(1)
            time_part = match.group(2)
            # datetimeオブジェクトに変換してからフォーマット
            dt_obj = datetime.strptime(f"{year}/{date_part} {time_part}", "%Y/%m/%d %H:%M")
            formatted_datetime = dt_obj.strftime("%Y.%m.%d %H:%M")

            # 通貨コードに変換
            currency = currency_map.get(country_name, None)
            if not currency:
                continue # マップにない通貨はスキップ

            # 重要度に変換
            star_count = impact_str.count('★')
            impact = impact_map.get(star_count, None)
            if not impact:
                continue # 重要度が不明なものはスキップ

            # 整形したデータをリストに追加
            event_data.append([formatted_datetime, currency, impact])

        if not event_data:
            print("指標データを抽出できませんでした。サイトの構造が変更された可能性があります。")
            return

        # 6. pandas DataFrameに変換してCSVファイルとして保存
        df = pd.DataFrame(event_data, columns=['DateTime', 'Currency', 'Impact'])
        
        # EAが読み込む形式でCSVを出力 (ヘッダーあり、インデックスなし)
        df.to_csv(output_file, index=False, header=True)
        
        print("-" * 30)
        print(f"完了！ {len(event_data)}件の指標データを '{output_file}' に保存しました。")
        print("このファイルをMT4の 'MQL4/Files' フォルダに配置してください。")
        print("-" * 30)

    except requests.exceptions.RequestException as e:
        print(f"エラー: Webサイトへのアクセスに失敗しました。 {e}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")


# --- スクリプトの実行 ---
if __name__ == "__main__":
    scrape_and_create_csv(url, output_csv_file)

