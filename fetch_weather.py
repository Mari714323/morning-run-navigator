import json
from datetime import datetime, timedelta
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
# 2. 日ごとの快適度スコアを計算する関数（季節対応版）
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
        dt = datetime.fromisoformat(date_str)
        current_month = dt.month

        max_precip = max(data["precips"])
        max_wind = max(data["winds"])
        avg_temp = sum(data["temps"]) / len(data["temps"])

        if current_month in [6, 7, 8, 9]:
            min_comfort_temp = 16.0
            max_comfort_temp = 26.0
        elif current_month in [12, 1, 2, 3]:
            min_comfort_temp = 5.0
            max_comfort_temp = 15.0
        else:
            min_comfort_temp = 10.0
            max_comfort_temp = 22.0

        score = 100

        if max_precip >= 50:
            score = 0
        else:
            score -= max_precip * 0.5

        if max_wind > 15:
            score -= (max_wind - 15) * 1.5

        if avg_temp < min_comfort_temp:
            score -= (min_comfort_temp - avg_temp) * 2
        elif avg_temp > max_comfort_temp:
            score -= (avg_temp - max_comfort_temp) * 2

        score = max(0, min(100, score))

        daily_scores[date_str] = {
            "score": round(score),
            "max_precip": max_precip,
            "max_wind": round(max_wind, 1),
            "avg_temp": round(avg_temp, 1),
            "season_zone": f"{min_comfort_temp}℃〜{max_comfort_temp}℃",
        }

    return daily_scores


# ==========================================
# 3. ユーザー設定に合わせてスケジュールを最適化する関数（動的ペナルティ版）
# ==========================================
def optimize_schedule(daily_scores, target_days=3, ng_days=[]):
    """連戦ペナルティをリアルタイムに計算しながら、今週のベストスケジュールを決定する"""
    candidates = []

    # 1. 候補日の洗い出し
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
                "original_score": info["score"],
                "detail": info,
            }
        )

    selected_days = []
    selected_dates = set()

    # 2. 1日ずつ、目標日数分（または候補日の上限まで）ループを回して選考する
    loops = min(target_days, len(candidates))

    for _ in range(loops):
        best_candidate = None
        best_current_score = -999

        for c in candidates:
            # すでに選ばれている日はスキップ
            if c["date"] in selected_dates:
                continue

            current_dt = datetime.fromisoformat(c["date"])

            # 前後2日分の日付文字列を作成して連戦チェックを行う
            d_minus_1 = (current_dt - timedelta(days=1)).strftime("%Y-%m-%d")
            d_minus_2 = (current_dt - timedelta(days=2)).strftime("%Y-%m-%d")
            d_plus_1 = (current_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            d_plus_2 = (current_dt + timedelta(days=2)).strftime("%Y-%m-%d")

            penalty = 0

            # 3日連続以上になるパターン (前後に挟まれる、または片側にすでに2連戦ある)
            is_3_consecutive = (
                (d_minus_1 in selected_dates and d_plus_1 in selected_dates)
                or (d_minus_1 in selected_dates and d_minus_2 in selected_dates)
                or (d_plus_1 in selected_dates and d_plus_2 in selected_dates)
            )

            # 2日連続になるパターン
            is_2_consecutive = (
                d_minus_1 in selected_dates or d_plus_1 in selected_dates
            )

            if is_3_consecutive:
                penalty = 50
            elif is_2_consecutive:
                penalty = 15

            # ペナルティを引いた「暫定スコア」で勝負する
            current_score = c["original_score"] - penalty

            if current_score > best_current_score:
                best_current_score = current_score
                best_candidate = c

        # 今回のループで最もスコアが高かった日を「採用」として確定
        if best_candidate:
            selected_days.append(
                {
                    "date": best_candidate["date"],
                    "weekday": best_candidate["weekday"],
                    "score": best_candidate["original_score"],  # 画面には元の天気の点数を出す
                    "detail": best_candidate["detail"],
                }
            )
            selected_dates.add(best_candidate["date"])

    # 3. 最終結果を日付順（カレンダー通り）に並び替える
    best_schedule = sorted(selected_days, key=lambda x: x["date"])

    return best_schedule


# ==========================================
# 4. 実際の実行部分
# ==========================================
if __name__ == "__main__":
    LATITUDE = 35.4437
    LONGITUDE = 139.6380
    TARGET_DAYS = 3  # ペナルティの動きを見るために、テスト用に3日に変更しています
    NG_DAYS = ["木", "日"]

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
                f"   (基準ゾーン: {info['season_zone']} | 平均体感: {info['avg_temp']}℃)"
            )

        print("\n=== ✨ 今週のベストスケジュール ✨ ===")
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