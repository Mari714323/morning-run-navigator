// APIサーバーのベースURL（AWS本番環境へ移行する際はここを書き換えます）
const API_BASE_URL = 'http://127.0.0.1:8000';

// ==========================================
// 1. 画面のHTML要素を取得
// ==========================================
const statusMessage = document.getElementById('status-message');
const resultSection = document.getElementById('result-section');
const displayPref = document.getElementById('display-pref');
const cardContainer = document.getElementById('card-container');
const detailsTableBody = document.getElementById('details-table-body');

let comfortChart = null;

// ==========================================
// 2. 一時メモリからデータを復元してAPIを叩く
// ==========================================
async function initResultPage() {
    const lat = sessionStorage.getItem('run_navigator_lat');
    const lon = sessionStorage.getItem('run_navigator_lon');
    const targetDays = sessionStorage.getItem('run_navigator_target_days');
    const prefName = sessionStorage.getItem('run_navigator_pref_name');
    const ngDaysRaw = sessionStorage.getItem('run_navigator_ng_days');

    // 🛡️ 安全対策：メモリが空っぽならトップページへ強制送還
    if (!lat || !lon || !targetDays) {
        window.location.href = 'index.html';
        return;
    }

    displayPref.textContent = prefName || "指定地域";
    const ngDays = ngDaysRaw ? JSON.parse(ngDaysRaw) : [];

    let ngDaysParams = '';
    ngDays.forEach(day => {
        ngDaysParams += `&ng_days=${encodeURIComponent(day)}`;
    });

    // 🔍 修正後：直書きURLを変数に変更
    const url = `${API_BASE_URL}/api/schedule?latitude=${lat}&longitude=${lon}&target_days=${targetDays}${ngDaysParams}`;

    try {
        const response = await fetch(url);
        const data = await response.json();
        const schedule = data.best_schedule;

        if (!schedule || schedule.length === 0) {
            statusMessage.textContent = "条件に合うランニング日和が見つかりませんでした…";
            return;
        }

        // --- ① おすすめスケジュールカードの自動生成 ---
        cardContainer.innerHTML = '';
        schedule.forEach(day => {
            const dateObj = new Date(day.date);
            const formattedDate = `${String(dateObj.getMonth() + 1).padStart(2, '0')}/${String(dateObj.getDate()).padStart(2, '0')}`;

            const card = document.createElement('div');
            // 【変更】外部CSSで定義した汎用的なクラス名に差し替え
            card.className = "comfort-card";

            card.innerHTML = `
                <div>
                    <div class="card-header">
                        <span class="card-date">${formattedDate} <span class="card-weekday">(${day.weekday})</span></span>
                        <span class="card-score">${day.score} 点</span>
                    </div>
                    <div class="card-details">
                        <div class="card-detail-item"><span>☔</span> 降水確率: ${day.detail.max_precip}%</div>
                        <div class="card-detail-item"><span>🌡️</span> 平均体感: ${day.detail.avg_temp}℃</div>
                    </div>
                </div>
            `;
            cardContainer.appendChild(card);
        });

        // --- ② Chart.js による快適度グラフの描画 ---
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

        // --- ③ 7日間の詳細データテーブルの生成 ---
        detailsTableBody.innerHTML = '';
        Object.keys(dailyScores).forEach(dateStr => {
            const info = dailyScores[dateStr];
            const dateObj = new Date(dateStr);
            const formattedDate = `${String(dateObj.getMonth() + 1).padStart(2, '0')}/${String(dateObj.getDate()).padStart(2, '0')}`;
            
            const dayLabels = ['日', '月', '火', '水', '木', '金', '土'];
            const jpWeekday = dayLabels[dateObj.getDay()];

            // 点数に応じたステータスクラスのマッピング
            let statusEmoji = '☔';
            let statusText = 'スキップ推奨';
            let statusClass = 'status-skipped';
            
            if (info.score >= 80) {
                statusEmoji = '✨'; statusText = '最高日和'; statusClass = 'status-excellent';
            } else if (info.score >= 50) {
                statusEmoji = '☁️'; statusText = 'まあまあ'; statusClass = 'status-good';
            } else if (info.score > 0) {
                statusEmoji = '⚠️'; statusText = '微妙かも'; statusClass = 'status-warning';
            }

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="padding-left: 0.5rem; font-weight: 700; color: #1e293b;">${formattedDate} <span style="font-size: 0.75rem; color: #94a3b8; font-weight: 400;">( ${jpWeekday} )</span></td>
                <td class="${statusClass}">${statusEmoji} ${info.score}点 <span class="status-subtext">(${statusText})</span></td>
                <td>☔ ${info.max_precip}%</td>
                <td>💨 ${info.max_wind} km/h</td>
                <td>🌡️ ${info.avg_temp} ℃</td>
            `;
            detailsTableBody.appendChild(tr);
        });

        // ローディングを非表示にし、結果ビュー全体を一斉表示
        statusMessage.classList.add('hidden');
        resultSection.classList.remove('hidden');

    } catch (error) {
        console.error("API通信エラー:", error);
        statusMessage.textContent = "天気データの取得中にエラーが発生しました。APIサーバーが起動しているか確認してください。";
    }
}

// ページ読み込みと同時に初期化
initResultPage();