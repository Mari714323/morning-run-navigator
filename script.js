// ==========================================
// 1. 画面のHTML要素を取得
// ==========================================
const btn = document.getElementById('fetch-btn');
const targetDaysSelect = document.getElementById('target-days');
const latitudeInput = document.getElementById('latitude');
const longitudeInput = document.getElementById('longitude');
const statusMessage = document.getElementById('status-message');
const resultSection = document.getElementById('result-section');
const cardContainer = document.getElementById('card-container');

const tabBtnSchedule = document.getElementById('tab-btn-schedule');
const tabBtnLogic = document.getElementById('tab-btn-logic');
const tabContentSchedule = document.getElementById('tab-content-schedule');
const tabContentLogic = document.getElementById('tab-content-logic');

// 【追加】描画したグラフのインスタンスを記憶しておく変数（再描画時のバグ防止用）
let comfortChart = null;

// ==========================================
// 2. スケジュール計算・更新ボタンが押された時の処理
// ==========================================
btn.addEventListener('click', async () => {
    // 画面の表示状態をリセット
    statusMessage.classList.remove('hidden');
    resultSection.classList.add('hidden');
    cardContainer.innerHTML = '';

    const lat = latitudeInput.value;
    const lon = longitudeInput.value;
    const targetDays = targetDaysSelect.value;
    
    // チェックがついているすべてのNG曜日を配列として取得
    const checkedBoxes = document.querySelectorAll('input[name="ng-day"]:checked');
    
    // API用のURLパラメータ（&ng_days=〇）を組み立て
    let ngDaysParams = '';
    checkedBoxes.forEach(box => {
        ngDaysParams += `&ng_days=${encodeURIComponent(box.value)}`;
    });
    
    // APIのURLを動的に組み立て
    const url = `http://127.0.0.1:8000/api/schedule?latitude=${lat}&longitude=${lon}&target_days=${targetDays}${ngDaysParams}`;

    try {
        const response = await fetch(url);
        const data = await response.json();
        
        const schedule = data.best_schedule;

        if (!schedule || schedule.length === 0) {
            statusMessage.textContent = "条件に合うランニング日和が見つかりませんでした…";
            return;
        }

        // 届いたJSONデータをループ処理して、HTMLのカードを自動生成
        schedule.forEach(day => {
            const dateObj = new Date(day.date);
            const formattedDate = `${String(dateObj.getMonth() + 1).padStart(2, '0')}/${String(dateObj.getDate()).padStart(2, '0')}`;

            const card = document.createElement('div');
            card.className = "bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex flex-col justify-between";

            card.innerHTML = `
                <div>
                    <div class="flex justify-between items-start mb-3">
                        <span class="text-slate-900 font-bold text-lg">${formattedDate} <span class="text-sm font-normal text-slate-500">(${day.weekday})</span></span>
                        <span class="bg-blue-50 text-blue-600 text-xs font-bold px-2 py-1 rounded-full">${day.score} 点</span>
                    </div>
                    <div class="space-y-1.5 text-sm text-slate-600">
                        <div class="flex items-center gap-1.5"><span>☔</span> 降水確率: ${day.detail.max_precip}%</div>
                        <div class="flex items-center gap-1.5"><span>🌡️</span> 平均体感: ${day.detail.avg_temp}℃</div>
                    </div>
                </div>
            `;
            cardContainer.appendChild(card);
        });

        // --- 【追加】📊 Chart.js による快適度グラフの描画処理 ---
        const dailyScores = data.daily_scores;
        const labels = [];
        const scoresData = [];

        // バックエンドから届いた 7日間のデータ（オブジェクト）をループしてグラフ用の配列を作る
        Object.keys(dailyScores).forEach(dateStr => {
            const dateObj = new Date(dateStr);
            // 日付のフォーマットを「06/17」のような形に整形
            const formattedDate = `${String(dateObj.getMonth() + 1).padStart(2, '0')}/${String(dateObj.getDate()).padStart(2, '0')}`;
            labels.push(formattedDate);
            scoresData.push(dailyScores[dateStr].score);
        });

        // すでに過去のグラフが存在している場合は、一度破棄（destroy）する（Chart.jsが重なるバグを防ぐため）
        if (comfortChart) {
            comfortChart.destroy();
        }

        // HTMLに作った canvas（comfort-chart）を見つけて、棒グラフを描画！
        const ctx = document.getElementById('comfort-chart').getContext('2d');
        comfortChart = new Chart(ctx, {
            type: 'bar', // 棒グラフを指定
            data: {
                labels: labels, // 横軸（日付）
                datasets: [{
                    label: '快適度スコア',
                    data: scoresData, // 縦軸（点数）
                    backgroundColor: 'rgba(59, 130, 246, 0.6)', // さわやかな薄い青
                    borderColor: 'rgb(59, 130, 246)', // 線の色
                    borderWidth: 1,
                    borderRadius: 8 // 棒の角を丸くして今風のフラットデザインにする
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100, // 快適度は100点満点
                        ticks: {
                            stepSize: 20
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false // グラフの上の凡例（ラベル）はスッキリ消す
                    }
                }
            }
        });
        // -----------------------------------------------------

        // ローディングを消して結果を表示
        statusMessage.classList.add('hidden');
        resultSection.classList.remove('hidden');

        // 新しく計算したときは、常に最初のおすすめスケジュールタブを開いた状態にする
        tabBtnSchedule.click();

    } catch (error) {
        statusMessage.textContent = "エラーが発生しました: " + error;
    }
});

// ==========================================
// 3. タブ切り替えの制御ロジック
// ==========================================
// 「おすすめスケジュール」タブがクリックされたとき
tabBtnSchedule.addEventListener('click', () => {
    tabBtnSchedule.className = "px-4 py-2 text-sm font-medium border-b-2 border-blue-600 text-blue-600 focus:outline-none";
    tabBtnLogic.className = "px-4 py-2 text-sm font-medium border-b-2 border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 focus:outline-none";
    
    tabContentSchedule.classList.remove('hidden');
    tabContentLogic.classList.add('hidden');
});

// 「算出ロジックの解説」タブがクリックされたとき
tabBtnLogic.addEventListener('click', () => {
    tabBtnSchedule.className = "px-4 py-2 text-sm font-medium border-b-2 border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 focus:outline-none";
    tabBtnLogic.className = "px-4 py-2 text-sm font-medium border-b-2 border-blue-600 text-blue-600 focus:outline-none";
    
    tabContentSchedule.classList.add('hidden');
    tabContentLogic.classList.remove('hidden');
});