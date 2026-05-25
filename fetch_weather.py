import json
from datetime import datetime
import requests


def fetch_7day_hourly_weather(latitude: float, longitude: float):
    """Open-Meteo APIから7日間の1時間ごとの天気データを取得する"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation_probability,wind_speed_10m,apparent_temperature",
        "timezone": "Asia/Tokyo",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"APIデータの取得に失敗しました: {e}")
        return None


def calculate_daily_scores(weather_data):
    """
    毎日 5:00 〜 8:00 のデータから、日ごとの快適度スコア（100点満点）を計算する
    """
    if not weather_data or "hourly" not in weather_data:
        return {}

    hourly = weather_data["hourly"]
    times = hourly["time"]
    precip_probs = hourly["precipitation_probability"]
    wind_speeds = hourly["wind_speed_10m"]
    apparent_temps = hourly["apparent_temperature"]

    # 日ごとにデータをグループ化するための辞書
    # 構造: { "2026-05-25": { "temps": [...], "precips": [...], "winds": [...] } }
    daily_raw_data = {}

    for i, time_str in enumerate(times):
        dt = datetime.fromisoformat(time_str)

        # 朝の 5:00 〜 8:00 のデータのみを収集
        if 5 <= dt.hour <= 8:
            date_str = dt.strftime("%Y-%m-%d")  # キーとなる日付文字列

            if date_str not in daily_raw_data:
                daily_raw_data[date_str] = {"temps": [], "precips": [], "winds": []}

            daily_raw_data[date_str]["temps"].append(apparent_temps[i])
            daily_raw_data[date_str]["precips"].append(precip_probs[i])
            daily_raw_data[date_str]["winds"].append(wind_speeds[i])

    # 日ごとのスコアを計算する
    daily_scores = {}

    for date_str, data in daily_raw_data.items():
        # --- 代表値の計算 ---
        max_precip = max(data["precips"])  # 朝の時間帯の最大降水確率
        max_wind = max(data["winds"])  # 朝の時間帯の最大風速
        avg_temp = sum(data["temps"]) / len(data["temps"])  # 平均体感温度

        # --- スコア計算ロジック（ここがこだわりポイント！） ---
        score = 100  # 初期値は100点

        # 1. 降水確率による減点
        if max_precip >= 50:
            score = 0  # 降水確率50%以上は強制的に0点（走らない）
        else:
            # 降水確率が10%〜40%なら、確率に応じて減点（例: 30%なら-15点）
            score -= max_precip * 0.5

        # 2. 風速による減点（km/h単位。一般的に15km/h(約4m/s)以上で風が気になる）
        if max_wind > 15:
            wind_penalty = (max_wind - 15) * 1.5
            score -= wind_penalty

        # 3. 体感温度による減点（走りやすい快適ゾーンを 10℃〜22℃ と仮定）
        if avg_temp < 10:
            # 寒すぎる場合の減点（10℃から下がるほど減点）
            score -= (10 - avg_temp) * 2
        elif avg_temp > 22:
            # 暑すぎる場合の減点（22℃から上がるほど減点）
            score -= (avg_temp - 22) * 2

        # スコアが0点未満、100点より大きくならないように調整
        score = max(0, min(100, score))

        # 計算結果と、その日の気象サマリーを保存
        daily_scores[date_str] = {
            "score": round(score),
            "max_precip": max_precip,
            "max_wind": round(max_wind, 1),
            "avg_temp": round(avg_temp, 1),
        }

    return daily_scores


if __name__ == "__main__":
    LATITUDE = 35.4437
    LONGITUDE = 139.6380

    print(f"位置情報: 緯度 {LATITUDE} / 経度 {LONGITUDE} の天気データを取得中...")
    raw_data = fetch_7day_hourly_weather(LATITUDE, LONGITUDE)

    if raw_data:
        # 快適度スコアの計算を実行
        scores = calculate_daily_scores(raw_data)

        print("\n=== 日ごとのランニング快適度スコア ===")
        for date_str, info in scores.items():
            dt = datetime.fromisoformat(date_str)
            formatted_date = dt.strftime("%m/%d (%a)")

            # スコアに応じた簡単な評価メッセージ
            score = info["score"]
            if score >= 80:
                comment = "✨ 最高！ランニング日和"
            elif score >= 50:
                comment = "☁️ まあまあ快適に走れそう"
            elif score > 0:
                comment = "⚠️ 少し走りづらいかも"
            else:
                comment = "☔ 雨予報（スキップ推奨）"

            print(f"{formatted_date} : {score:3}点 | {comment}")
            print(
                f"   (最高降水確率: {info['max_precip']}% | 最大風速: {info['max_wind']}km/h | 平均体感: {info['avg_temp']}℃)\n"
            )