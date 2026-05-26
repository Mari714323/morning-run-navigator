import json
from datetime import datetime
import requests


# ==========================================
# 1. 外部APIからデータを取得する関数
# ==========================================
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


# ==========================================
# 2. 日ごとの快適度スコアを計算する関数
# ==========================================
def calculate_daily_scores(weather_data):
    """毎日 5:00 〜 8:00 のデータから、日ごとの快適度スコア（100点満点）を計算する"""
    if not weather_data or "hourly" not in weather_data:
        return {}

    hourly = weather_data["hourly"]
    times = hourly["time"]
    precip_probs = hourly["precipitation_probability"]
    wind_speeds = hourly["wind_speed_10m"]
    apparent_temps = hourly["apparent_temperature"]

    daily_raw_data = {}

    for i, time_str in enumerate(times):
        dt = datetime.fromisoformat(time_str)

        if 5 <= dt.hour <= 8:
            date_str = dt.strftime("%Y-%m-%d")

            if date_str not in daily_raw_data:
                daily_raw_data[date_str] = {"temps": [], "precips": [], "winds": []}

            daily_raw_data[date_str]["temps"].append(apparent_temps[i])
            daily_raw_data[date_str]["precips"].append(precip_probs[i])
            daily_raw_data[date_str]["winds"].append(wind_speeds[i])

    daily_scores = {}

    for date_str, data in daily_raw_data.items():
        max_precip = max(data["precips"])
        max_wind = max(data["winds"])
        avg_temp = sum(data["temps"]) / len(data["temps"])

        score = 100

        if max_precip >= 50:
            score = 0
        else:
            score -= max_precip * 0.5

        if max_wind > 15:
            score -= (max_wind - 15) * 1.5

        if avg_temp < 10:
            score -= (10 - avg_temp) * 2
        elif avg_temp > 22:
            score -= (avg_temp - 22) * 2

        score = max(0, min(100, score))

        daily_scores[date_str] = {
            "score": round(score),
            "max_precip": max_precip,
            "max_wind": round(max_wind, 1),
            "avg_temp": round(avg_temp, 1),
        }

    return daily_scores


# ==========================================
# 3. ユーザー設定に合わせてスケジュールを最適化する関数
# ==========================================
def optimize_schedule(daily_scores, target_days=3, ng_days=[]):
    """快適度スコア、目標日数、NG曜日に基づいて、今週のベストスケジュールを決定する"""
    candidates = []

    for date_str, info in daily_scores.items():
        dt = datetime.fromisoformat(date_str)
        day_of_week = dt.strftime("%A")

        weekday_map = {
            "Monday": "月",
            "Tuesday": "火",
            "Wednesday": "水",
            "Thursday": "木",
            "Friday": "金",
            "Saturday": "土",
            "Sunday": "日",
        }
        jp_weekday = weekday_map[day_of_week]

        if jp_weekday in ng_days:
            continue

        if info["score"] == 0:
            continue

        candidates.append(
            {
                "date": date_str,
                "weekday": jp_weekday,
                "score": info["score"],
                "detail": info,
            }
        )

    sorted_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    best_schedule = sorted_candidates[:target_days]
    best_schedule = sorted(best_schedule, key=lambda x: x["date"])

    return best_schedule


# ==========================================
# 4. 実際の実行部分
# ==========================================
if __name__ == "__main__":
    LATITUDE = 35.4437
    LONGITUDE = 139.6380
    TARGET_DAYS = 2  # 週に走りたい日数
    NG_DAYS = ["木", "日"]  # 走れないNG曜日

    print("--- ユーザー設定 ---")
    print(f"目標日数: 週 {TARGET_DAYS} 日")
    print(f"NG曜日: {', '.join(NG_DAYS) if NG_DAYS else 'なし'}")

    print(f"\n位置情報: 緯度 {LATITUDE} / 経度 {LONGITUDE} の天気データを取得中...")
    raw_data = fetch_7day_hourly_weather(LATITUDE, LONGITUDE)

    if raw_data:
        scores = calculate_daily_scores(raw_data)

        print("\n=== 日ごとのランニング快適度スコア ===")
        for date_str, info in scores.items():
            dt = datetime.fromisoformat(date_str)
            formatted_date = dt.strftime("%m/%d (%a)")

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

        print("=== ✨ 今週のベストスケジュール ✨ ===")
        best_days = optimize_schedule(scores, target_days=TARGET_DAYS, ng_days=NG_DAYS)

        if not best_days:
            print(
                "条件に合うランニング日和が見つかりませんでした…（すべて雨かNG曜日です）"
            )
        else:
            for day in best_days:
                dt = datetime.fromisoformat(day["date"])
                formatted_date = dt.strftime("%m/%d")
                print(
                    f"🏃 【{formatted_date} ({day['weekday']})】 快適度: {day['score']}点"
                )
                print(
                    f"    (降水確率: {day['detail']['max_precip']}% | 体感温度: {day['detail']['avg_temp']}℃)"
                )