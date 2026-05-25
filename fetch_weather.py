import json
from datetime import datetime
import requests


def fetch_7day_hourly_weather(latitude: float, longitude: float):
    """Open-Meteo APIから7日間の1時間ごとの天気データを取得する"""
    # 必要なパラメータを指定（降水確率、風速、体感温度）
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation_probability,wind_speed_10m,apparent_temperature",
        "timezone": "Asia/Tokyo",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # エラーがあれば例外を発生させる
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"APIデータの取得に失敗しました: {e}")
        return None


def extract_morning_data(weather_data):
    """取得したデータから毎日 5:00 〜 8:00 のデータのみを抽出して表示する"""
    if not weather_data or "hourly" not in weather_data:
        print("有効なデータがありません。")
        return

    hourly = weather_data["hourly"]
    times = hourly["time"]  # ISO8601形式の文字列リスト
    precip_probs = hourly["precipitation_probability"]  # 降水確率 (%)
    wind_speeds = hourly["wind_speed_10m"]  # 風速 (km/h または m/s *設定による)
    apparent_temps = hourly["apparent_temperature"]  # 体感温度 (℃)

    print("\n=== 朝の時間帯（5:00 - 8:00）のデータ確認 ===")

    # 1時間ごとのデータをループ処理
    for i, time_str in enumerate(times):
        # 文字列（例: "2026-05-25T05:00"）をdatetimeオブジェクトに変換
        dt = datetime.fromisoformat(time_str)

        # ターゲット時間帯（5:00 〜 8:00）のみフィルター
        if 5 <= dt.hour <= 8:
            date_label = dt.strftime("%Y-%m-%d (%a)")
            time_label = dt.strftime("%H:%M")

            prob = precip_probs[i]
            wind = wind_speeds[i]
            temp = apparent_temps[i]

            print(
                f"[{date_label} {time_label}] 降水確率: {prob:3}% | 風速: {wind:4} km/h | 体感温度: {temp:5}℃"
            )


if __name__ == "__main__":
    # サンプル座標: 横浜（ユーザーの環境や好みに合わせて変更してください）
    LATITUDE = 35.4437
    LONGITUDE = 139.6380

    print(f"位置情報: 緯度 {LATITUDE} / 経度 {LONGITUDE} の天気データを取得中...")
    raw_data = fetch_7day_hourly_weather(LATITUDE, LONGITUDE)

    # 1. 生のJSON構造を少しだけ覗き見（キーの確認）
    if raw_data:
        print("\n--- APIレスポンスのルートキー一覧 ---")
        print(list(raw_data.keys()))

        # 2. 目的の時間帯に絞ってコンソール出力
        extract_morning_data(raw_data)
