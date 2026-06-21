// 💡 APIサーバーのベースURL（AWS本番環境へ移行する際はここを書き換えます）
const API_BASE_URL = 'http://127.0.0.1:8000';

// ==========================================
// 1. 画面のHTML要素を取得
// ==========================================
const btn = document.getElementById('fetch-btn');
const targetDaysSelect = document.getElementById('target-days');
const latitudeInput = document.getElementById('latitude');
const longitudeInput = document.getElementById('longitude');
const locationSelect = document.getElementById('location-select');

// ==========================================
// 2. ボタンが押されたら、条件を記憶して画面遷移（ジャンプ）
// ==========================================
btn.addEventListener('click', () => {
    const lat = latitudeInput.value;
    const lon = longitudeInput.value;
    const targetDays = targetDaysSelect.value;
    const prefName = locationSelect.value;
    
    // チェックがついているすべてのNG曜日を配列として取得
    const checkedBoxes = document.querySelectorAll('input[name="ng-day"]:checked');
    const ngDays = [];
    checkedBoxes.forEach(box => {
        ngDays.push(box.value);
    });

    // 💡【最重要】ブラウザの一時メモリ（sessionStorage）に条件を記憶！
    // 配列やオブジェクトはそのまま保存できないため、JSON.stringifyで文字列に変換して保存します
    sessionStorage.setItem('run_navigator_lat', lat);
    sessionStorage.setItem('run_navigator_lon', lon);
    sessionStorage.setItem('run_navigator_target_days', targetDays);
    sessionStorage.setItem('run_navigator_pref_name', prefName);
    sessionStorage.setItem('run_navigator_ng_days', JSON.stringify(ngDays));

    // 🚀 記憶したら、結果表示用の別画面（result.html）へ画面遷移！
    window.location.href = 'result.html';
});

// ==========================================
// 3. API（CSV）から都道府県データを取得 ＆ 連動ロジック
// ==========================================
let locationsData = [];

async function fetchLocations() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/locations`);
        locationsData = await response.json();

        locationSelect.innerHTML = '';

        locationsData.forEach(loc => {
            const option = document.createElement('option');
            option.value = loc.pref_name;
            option.textContent = loc.pref_name;
            
            if (loc.pref_name === '神奈川県') {
                option.selected = true;
            }
            locationSelect.appendChild(option);
        });

        updateCoordinates('神奈川県');

    } catch (error) {
        console.error('都道府県データの取得に失敗しました:', error);
        locationSelect.innerHTML = '<option value="">データの読み込みに失敗しました</option>';
    }
}

function updateCoordinates(prefName) {
    const target = locationsData.find(loc => loc.pref_name === prefName);
    if (target) {
        latitudeInput.value = target.lat;
        longitudeInput.value = target.lon;
    }
}

locationSelect.addEventListener('change', () => {
    updateCoordinates(locationSelect.value);
});

// 画面の読み込みと同時にAPIから都道府県を読み込み
fetchLocations();