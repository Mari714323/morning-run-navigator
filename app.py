from datetime import datetime
import streamlit as st

# fetch_weather.py から関数をインポート
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

# 週に走りたい日数（スライダーで選択・上限4日）
target_days = st.sidebar.slider("週に走りたい日数", min_value=1, max_value=4, value=3)

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
        # 3. 画面表示エリア（3つのタブ構成）
        # ==========================================
        tab1, tab2, tab3 = st.tabs([
            "✨ おすすめスケジュール", 
            "📅 7日間の詳細データ", 
            "💡 算出ロジックの解説"
        ])

        # --- タブ1: おすすめスケジュールと棒グラフ ---
        with tab1:
            st.header("今週のベストスケジュール")

            if not best_days:
                st.warning(
                    "条件に合うランニング日和が見つかりませんでした…（すべて雨かNG曜日です）"
                )
            else:
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

            st.markdown("---")
            st.subheader("📊 ひと目でわかる！今週の快適度グラフ")

            chart_data = {}
            for date_str, info in scores.items():
                dt = datetime.fromisoformat(date_str)
                formatted_date = dt.strftime("%m/%d")
                chart_data[formatted_date] = info["score"]

            st.bar_chart(chart_data)

        # --- タブ2: 詳細データを格納 ---
        with tab2:
            st.header("7日間の快適度詳細一覧")

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

        # --- タブ3: 算出ロジックの解説（新機能） ---
        with tab3:
            st.header("💡 スケジュール算出ロジックの解説")
            st.write("当アプリでは、使う人が根拠を持って安心して予定を組めるよう、以下のルールに則って論理的にロジックを計算しています。")

            st.subheader("1. データソースについて")
            st.markdown("""
            * 世界的な気象API（Open-Meteo）から、1時間ごとの最新予報をリアルタイムに取得しています。
            * ランニング・ウォーキングに最適な**「朝 5:00 〜 8:00」の時間帯データのみ**をピンポイントに抽出して集計しています。
            """)

            st.subheader("2. 天気の集計ルール")
            st.markdown("""
            朝の3時間の中で、それぞれの項目ごとに最もシビアな数値を採用しています。
            * **降水確率**：少しの雨でも避けられるよう、時間内の**「最大値」**を採用。
            * **風速**：突風による走りづらさを防ぐため、時間内の**「最大値」**を採用。
            * **体感温度**：全体の寒暖感を捉えるため、時間内の**「平均値」**を採用。
            """)

            st.subheader("3. 快適度スコアの計算（100点満点からの減点方式）")
            st.markdown("""
            * **雨チェック**：降水確率が50%以上の日は、安全のため一発で「0点（スキップ推奨）」になります。50%未満の場合は、確率に応じて少しずつ減点されます。
            * **强風チェック**：風速が15km/hを超えると、風の強さに応じて減点されます。
            * **季節に応じた快適温度（自動判定）**：データの日付から現在の「月」を自動判定し、季節ごとに快適ゾーンを切り替えています。ゾーンから外れると、1℃ごとに2点ずつ減点されます。
                * *春・秋（4, 5, 10, 11月）*：10℃ 〜 22℃
                * *夏（6, 7, 8, 9月）*：16℃ 〜 26℃
                * *冬（12, 1, 2, 3月）*：5℃ 〜 15℃
            """)

            st.subheader("4. 足腰を守る！連戦セーフティ機能")
            st.markdown("""
            天気が良くても毎日連続して走ると足腰に負担がかかるため、スケジュール決定時に自動でブレーキをかける「動的ペナルティ」を導入しています。
            * スケジュールが**2日連続**になる日 ➔ スコアを **-15点**
            * スケジュールが**3日連続以上**になる日 ➔ スコアを **-50点**
            
            ※ただし、「雨の日を走るくらいなら、晴れの日の2連戦の方がマシ」とプログラムが判断できるよう、天気が最高に良い場合は連戦が許容される絶妙なバランスで計算しています。
            """)