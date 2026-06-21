// ==========================================
// 1. 画面のHTML要素を取得
// ==========================================
const statusMessage = document.getElementById('status-message');
const resultSection = document.getElementById('result-section');
const displayPref = document.getElementById('display-pref');
const cardContainer = document.getElementById('card-container');
const detailsTableBody = document.getElementById('details-table-body');

const tabBtnSchedule = document.getElementById('tab-btn-schedule');
const tabBtnDetails = document.getElementById('tab-btn-details');
const tabBtnLogic = document.getElementById('tab-btn-logic');

const tabContentSchedule = document.getElementById('tab-content-schedule');
const tabContentDetails = document.getElementById('tab-content-details');
const tabContentLogic = document.getElementById('tab-content-logic');

let comfortChart = null;

// ==========================================
// 2. 画面が開いた瞬間に一時メモリからデータを復元してAPIを叩く
// ==========================================
async function initResultPage() {
    // 💡 sessionStorage からトップページで保存した条件を読み出す
    const lat = sessionStorage.getItem('run_navigator_lat');
    const lon = sessionStorage.getItem('run_navigator_lon');
    const targetDays = sessionStorage.getItem('run_navigator_target_days');
    const prefName = sessionStorage.getItem('run_navigator_pref_name');
    const ngDaysRaw = sessionStorage.getItem('run_navigator_ng_days');

    // 🛡️ 安全対策：もしメモリが空っぽならトップページへ強制送還する
    if (!lat || !lon || !targetDays) {
        window.location.href = 'index.html';
        return;
    }

    // 画面の地域バッジに都道府県名を表示
    displayPref.textContent = prefName || "指定地域";

    // NG曜日の配列をJSONから復元
    const ngDays = ngDaysRaw ? JSON.parse(ngDaysRaw) : [];

    // バックエンド（FastAPI）用のURLパラメータを組み立て
    let ngDaysParams = '';
    ngDays.forEach(day => {
        ngDaysParams += `&ng_days=${encodeURIComponent(day)}`;
    });

    // 127.0.0.1:8000 のAPIサーバーにリクエストを投げる
    const url = `http://127.0.0.1:8000/api/schedule?latitude=${lat}&longitude=${lon}&target_days=${targetDays}${ngDaysParams}`;

    try {
        const response = await fetch(url);
        const data = await response.json();
        const schedule = data.best_schedule;

        if (!schedule || schedule.length === 0) {
            statusMessage.textContent = "条件に合うランニング日和が見つかりませんでした…";
            return;
        }

        // --- 【移植】① おすすめスケジュールカードの自動生成 ---
        cardContainer.innerHTML = '';
        schedule.forEach(day => {
            const dateObj = new Date(day.date);
            const formattedDate = `${String(dateObj.getMonth() + 1).padStart(2, '0')}/${String(dateObj.getDate()).padStart(2, '0')}`;

            const card = document.createElement('div');
            card.className = "bg-white p-6 rounded-2xl shadow-modern flex flex-col justify-between transition-all hover:shadow-modern-lg";

            card.innerHTML = `
                <div>
                    <div class="flex justify-between items-start mb-4">
                        <span class="text-slate-900 font-bold text-lg">${formattedDate} <span class="text-sm font-normal text-slate-400">(${day.weekday})</span></span>
                        <span class="bg-blue-50 text-blue-600 text-xs font-bold px-2.5 py-1 rounded-full">${day.score} 点</span>
                    </div>
                    <div class="space-y-2 text-sm text-slate-500 font-medium">
                        <div class="flex items-center gap-1.5"><span>☔</span> 降水確率: ${day.detail.max_precip}%</div>
                        <div class="flex items-center gap-1.5"><span>🌡️</span> 平均体感: ${day.detail.avg_temp}℃</div>
                    </div>
                </div>
            `;
            cardContainer.appendChild(card);
        });

        // --- 【移植】② Chart.js による快適度グラフの描画 ---
        const dailyScores = data.daily_scores;
        const labels = [];
        const scoresData = [];

        Object.keys(dailyScores).forEach(dateStr => {
            const dateObj = new Date(dateStr);
            const formattedDate = `${String(dateObj.getMonth() + 1).padStart(2, '0')}/${String(dateObj.getDate()).padStart(2, '0')}`;
            labels.push(formattedDate);
            scoresData.push(dailyScores[dateStr].score);
        });

        const ctx = document.getElementById('comfort-chart').getContext('2d');
        comfortChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '快適度スコア',
                    data: scoresData,
                    backgroundColor: 'rgba(59, 130, 246, 0.6)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 1,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, max: 100, ticks: { stepSize: 20 } }
                },
                plugins: { legend: { display: false } }
            }
        });

        // --- 【移植】③ 7日間の詳細データテーブルの生成 ---
        detailsTableBody.innerHTML = '';
        Object.keys(dailyScores).forEach(dateStr => {
            const info = dailyScores[dateStr];
            const dateObj = new Date(dateStr);
            const formattedDate = `${String(dateObj.getMonth() + 1).padStart(2, '0')}/${String(dateObj.getDate()).padStart(2, '0')}`;
            
            const dayLabels = ['日', '月', '火', '水', '木', '金', '土'];
            const jpWeekday = dayLabels[dateObj.getDay()];

            let statusEmoji = '☔';
            let statusText = 'スキップ推奨';
            let statusColor = 'text-slate-400';
            
            if (info.score >= 80) {
                statusEmoji = '✨';
                statusText = '最高日和';
                statusColor = 'text-emerald-600 font-bold';
            } else if (info.score >= 50) {
                statusEmoji = '☁️';
                statusText = 'まあまあ';
                statusColor = 'text-blue-600';
            } else if (info.score > 0) {
                statusEmoji = '⚠️';
                statusText = '微妙かも';
                statusColor = 'text-amber-600';
            }

            const tr = document.createElement('tr');
            tr.className = "hover:bg-slate-50/80 transition-colors";
            tr.innerHTML = `
                <td class="py-4 pl-2 font-medium text-slate-900">${formattedDate} <span class="text-xs text-slate-400 font-normal">(${jpWeekday})</span></td>
                <td class="py-4 ${statusColor}">${statusEmoji} ${info.score}点 <span class="text-xs text-slate-400 font-normal">(${statusText})</span></td>
                <td class="py-4 font-medium text-slate-600">☔ ${info.max_precip}%</td>
                <td class="py-4 font-medium text-slate-600">💨 ${info.max_wind} km/h</td>
                <td class="py-4 font-medium text-slate-600">🌡️ ${info.avg_temp} ℃</td>
            `;
            detailsTableBody.appendChild(tr);
        });

        // ローディングを消して、結果エリアをドラマチックに表示
        statusMessage.classList.add('hidden');
        resultSection.classList.remove('hidden');

    } catch (error) {
        console.error("API通信エラー:", error);
        statusMessage.textContent = "天気データの取得中にエラーが発生しました。APIサーバーが起動しているか確認してください。";
    }
}

// ==========================================
// 3. タブ切り替えの制御ロジック
// ==========================================
const activeTabClass = "px-5 py-3 text-sm font-bold border-b-2 border-blue-600 text-blue-600 focus:outline-none";
const inactiveTabClass = "px-5 py-3 text-sm font-bold border-b-2 border-transparent text-slate-400 hover:text-slate-600 hover:border-slate-300 focus:outline-none";

tabBtnSchedule.addEventListener('click', () => {
    tabBtnSchedule.className = activeTabClass; tabBtnDetails.className = inactiveTabClass; tabBtnLogic.className = inactiveTabClass;
    tabContentSchedule.classList.remove('hidden'); tabContentDetails.classList.add('hidden'); tabContentLogic.classList.add('hidden');
});

tabBtnDetails.addEventListener('click', () => {
    tabBtnSchedule.className = inactiveTabClass; tabBtnDetails.className = activeTabClass; tabBtnLogic.className = inactiveTabClass;
    tabContentSchedule.classList.add('hidden'); tabContentDetails.classList.remove('hidden'); tabContentLogic.classList.add('hidden');
});

tabBtnLogic.addEventListener('click', () => {
    tabBtnSchedule.className = inactiveTabClass; tabBtnDetails.className = inactiveTabClass; tabBtnLogic.className = activeTabClass;
    tabContentSchedule.classList.add('hidden'); tabContentDetails.classList.add('hidden'); tabContentLogic.classList.remove('hidden');
});

// ページ読み込みと同時に初期化処理をキック
initResultPage();