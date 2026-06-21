from typing import List
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
# 【追加】Mangum をインポート
from mangum import Mangum

from fetch_weather import (
    calculate_daily_scores,
    fetch_7day_hourly_weather,
    optimize_schedule,
)

app = FastAPI()

import csv
import os

def load_locations_from_csv():
    """data/locations.csv から都道府県データを読み込む関数"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "..", "data", "locations.csv")
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
    return load_locations_from_csv()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

    return {
        "best_schedule": best_days,
        "daily_scores": scores
    }

# ==========================================
# 🚀 【追加】AWS Lambda 用のハンドラー定義
# ==========================================
# AWS API Gateway から届いた電波を、FastAPIが処理できるように Mangum で仲介します
handler = Mangum(app)