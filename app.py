from datetime import datetime
import streamlit as st

# 前回作った fetch_weather.py から関数をインポート
from fetch_weather import (
    calculate_daily_scores,
    fetch_7day_hourly_weather,
    optimize_schedule,
)

# 画面のタイトル設定
st.title("🏃 朝の最適ランニング・ウォーキング計画ナビ")
st.write("天気予報に応じて、今週のランニングスケジュールを自動で最適化します。")

# ==========================================
# 1. サイドバー（ユーザー設定エリア）
# ==========================================
st.sidebar.header("ユーザー設定")

# 緯度・経度の入力（デフォルトは横浜）
latitude = st.sidebar.number_input("緯度", value=35.4437, format="%.4f")
longitude = st.sidebar.number_input("経度", value=139.6380, format="%.4f")

# 週に走りたい日数（スライダーで選択）
target_days = st.sidebar.slider("週に走りたい日数", min_value=1, max_value=7, value=3)

# 走れないNG曜日（複数選択ボックス）
ng_days = st.sidebar.multiselect(
    "走れないNG曜日", ["月", "火", "水", "木", "金", "土", "日"], default=["木", "日"]
)

# ==========================================
# 2. メイン処理（データ取得と計算）
# ==========================================
if st.sidebar.button("スケジュールを計算・更新"):
    with st.spinner("最新の天気予報を取得中..."):
        raw_data = fetch_7day_hourly_weather(latitude, longitude)

    if raw_data:
        scores = calculate_daily_scores(raw_data)
        best_days = optimize_schedule(
            scores, target_days=target_days, ng_days=ng_days
        )

        # ==========================================
        # 3. 画面表示エリア
        # ==========================================
        st.header("✨ 今週のベストスケジュール")

        if not best_days:
            st.warning(
                "条件に合うランニング日和が見つかりませんでした…（すべて雨かNG曜日です）"
            )
        else:
            # 横並びのカード（カラム）でベストスケジュールを表示
            cols = st.columns(len(best_schedule := best_days))
            for i, day in enumerate(best_schedule):
                dt = datetime.fromisoformat(day["date"])
                formatted_date = dt.strftime("%m/%d")

                with cols[i]:
                    st.metric(
                        label=f"{formatted_date} ({day['weekday']})",
                        value=f"{day['score']} 点",
                    )
                    st.caption(f"☔ 降水: {day['detail']['max_precip']}%")
                    st.caption(f"🌡️ 体感: {day['detail']['avg_temp']}℃")

        # 日ごとの詳細リストも下に表示
        st.markdown("---")
        st.subheader("📅 7日間の快適度詳細一覧")

        for date_str, info in scores.items():
            dt = datetime.fromisoformat(date_str)
            formatted_date = dt.strftime("%m/%d (%a)")

            score = info["score"]
            if score >= 80:
                status = "✨ 最高！ランニング日和"
            elif score >= 50:
                status = "☁️ まあまあ"
            elif score > 0:
                status = "⚠️ 微妙かも"
            else:
                status = "☔ スキップ推奨"

            st.write(
                f"**{formatted_date}** : {score}点 （{status}） | "
                f"降水確率: {info['max_precip']}% / 風速: {info['max_wind']}km/h / 体感温度: {info['avg_temp']}℃"
            )