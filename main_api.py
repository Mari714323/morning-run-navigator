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