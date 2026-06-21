from typing import List
from fastapi import FastAPI, Query
# CORSの許可証を発行するための部品をインポート
from fastapi.middleware.cors import CORSMiddleware

from fetch_weather import (
    calculate_daily_scores,
    fetch_7day_hourly_weather,
    optimize_schedule,
)

app = FastAPI()

# 【追加】CSVファイルを読み込むための部品
import csv
import os

def load_locations_from_csv():
    """data/locations.csv から都道府県データを読み込む関数"""
    # 【修正】main_api.pyがある場所を基準にした絶対パスにすることで、どこから起動しても100%確実にCSVを読み込めるようにします
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "data", "locations.csv")
    locations = []
    if os.path.exists(csv_path):
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                locations.append({
                    "pref_name": row["pref_name"],
                    "lat": float(row["latitude"]),
                    "lon": float(row["longitude"])
                })
    return locations

@app.get("/api/locations")
def get_locations():
    """都道府県リストをフロントエンドに返す新しいAPI"""
    return load_locations_from_csv()


# --- 【追加】CORSの設定（防犯カメラの許可リスト） ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # すべてのウェブサイト（画面）からのアクセスを許可
    allow_credentials=True,
    allow_methods=["*"],  # GETやPOSTなど、すべての通信方法を許可
    allow_headers=["*"],  # すべてのデータヘッダーを許可
)


@app.get("/")
def read_root():
    return {"message": "Hello, Run Navigator API!"}


@app.get("/api/schedule")
def get_schedule(
    latitude: float,
    longitude: float,
    target_days: int = 3,
    ng_days: List[str] = Query([]),
):
    raw_data = fetch_7day_hourly_weather(latitude, longitude)
    if not raw_data:
        return {"error": "天気データの取得に失敗しました。"}

    scores = calculate_daily_scores(raw_data)
    best_days = optimize_schedule(
        scores, target_days=target_days, ng_days=ng_days
    )

    # 【変更】おすすめ日だけでなく、グラフ描画用に7日間すべてのスコア（scores）も一緒に返却します
    return {
        "best_schedule": best_days,
        "daily_scores": scores
    }