const container = document.getElementById('danmaku-container');
let ws = null;
const MAX_ITEMS = 20; // 最多显示20条弹幕

function connectWebSocket() {
    ws = new WebSocket(`ws://${location.host}/ws/obs`);
    
    ws.onopen = () => {
        console.log('WebSocket 已连接');
    };
    
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'danmaku') {
            addDanmaku(msg.data);
        } else if (msg.type === 'gift') {
            addGift(msg.data);
        } else if (msg.type === 'sc') {
            addSuperChat(msg.data);
        } else if (msg.type === 'guard') {
            addGuard(msg.data);
        }
    };
    
    ws.onclose = () => {
        console.log('WebSocket 已断开，3秒后重连...');
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
    };
}

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('zh-CN', { hour12: false });
}

function addDanmaku(data) {
    const item = document.createElement('div');
    item.className = 'danmaku-item';
    
    let badgeHtml = '';
    if (data.guard_level) {
        const guardNames = {1: '总督', 2: '提督', 3: '舰长'};
        badgeHtml = `<span class="danmaku-badge guard-${data.guard_level}">${guardNames[data.guard_level]}</span>`;
    }
    
    item.innerHTML = `
        <div class="danmaku-user">
            <span class="danmaku-username">${escapeHtml(data.username)}</span>
            ${badgeHtml}
            <span class="danmaku-time">${getCurrentTime()}</span>
        </div>
        <div class="danmaku-message">${escapeHtml(data.message)}</div>
        ${data.dglab ? `
        <div class="dglab-info">
            <div class="dglab-strength">
                <span class="dglab-strength-icon">⚡</span>
                <span>+${data.dglab.strength}</span>
            </div>
            <div class="dglab-duration">
                <span class="dglab-duration-icon">⏱️</span>
                <span>${data.dglab.duration}</span>
            </div>
        </div>
        ` : ''}
    `;
    
    container.insertBefore(item, container.firstChild);
    limitItems();
}

function addGift(data) {
    const item = document.createElement('div');
    item.className = 'danmaku-item gift';
    
    item.innerHTML = `
        <div class="danmaku-user">
            <span class="danmaku-username">${escapeHtml(data.username)}</span>
            <span class="danmaku-time">${getCurrentTime()}</span>
        </div>
        <div class="danmaku-message">
            赠送 <span class="gift-name">${escapeHtml(data.gift_name)}</span> 
            <span class="gift-count">x${data.count}</span>
            <span class="gift-price">¥${data.price}</span>
        </div>
        ${data.dglab ? `
        <div class="dglab-info">
            <div class="dglab-strength">
                <span class="dglab-strength-icon">⚡</span>
                <span>+${data.dglab.strength}</span>
            </div>
            <div class="dglab-duration">
                <span class="dglab-duration-icon">⏱️</span>
                <span>${data.dglab.duration}</span>
            </div>
        </div>
        ` : ''}
    `;
    
    container.insertBefore(item, container.firstChild);
    limitItems();
}

function addSuperChat(data) {
    const item = document.createElement('div');
    item.className = 'danmaku-item sc';
    
    item.innerHTML = `
        <div class="danmaku-user">
            <span class="danmaku-username">${escapeHtml(data.username)}</span>
            <span class="danmaku-badge">SC ¥${data.price}</span>
            <span class="danmaku-time">${getCurrentTime()}</span>
        </div>
        <div class="danmaku-message">${escapeHtml(data.message)}</div>
        ${data.dglab ? `
        <div class="dglab-info">
            <div class="dglab-strength">
                <span class="dglab-strength-icon">⚡</span>
                <span>+${data.dglab.strength}</span>
            </div>
            <div class="dglab-duration">
                <span class="dglab-duration-icon">⏱️</span>
                <span>${data.dglab.duration}</span>
            </div>
        </div>
        ` : ''}
    `;
    
    container.insertBefore(item, container.firstChild);
    limitItems();
}

function addGuard(data) {
    const item = document.createElement('div');
    item.className = 'danmaku-item guard';
    
    const guardNames = {1: '总督', 2: '提督', 3: '舰长'};
    
    item.innerHTML = `
        <div class="danmaku-user">
            <span class="danmaku-username">${escapeHtml(data.username)}</span>
            <span class="danmaku-badge guard-${data.guard_level}">开通${guardNames[data.guard_level]}</span>
            <span class="danmaku-time">${getCurrentTime()}</span>
        </div>
        ${data.dglab ? `
        <div class="dglab-info">
            <div class="dglab-strength">
                <span class="dglab-strength-icon">⚡</span>
                <span>+${data.dglab.strength}</span>
            </div>
            <div class="dglab-duration">
                <span class="dglab-duration-icon">⏱️</span>
                <span>${data.dglab.duration}</span>
            </div>
        </div>
        ` : ''}
    `;
    
    container.insertBefore(item, container.firstChild);
    limitItems();
}

function limitItems() {
    // 当超过最大数量时，移除最旧的（最后一个）
    while (container.children.length > MAX_ITEMS) {
        container.removeChild(container.lastChild);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 初始化
connectWebSocket();
loadHistory();

// 复制 OBS URL
function copyObsUrl() {
    const urlInput = document.getElementById('obs-url');
    if (urlInput) {
        const obsUrl = `${window.location.protocol}//${window.location.host}/obs-source.html`;
        urlInput.value = obsUrl;
        urlInput.select();
        document.execCommand('copy');
        alert('链接已复制到剪贴板！');
    }
}

// 页面加载时设置 URL
window.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('obs-url');
    if (urlInput) {
        const obsUrl = `${window.location.protocol}//${window.location.host}/obs-source.html`;
        urlInput.value = obsUrl;
    }
});

async function loadHistory() {
    try {
        const resp = await fetch('/api/obs/history');
        const history = await resp.json();
        history.forEach(item => {
            if (item.type === 'danmaku') {
                addDanmaku(item.data);
            } else if (item.type === 'gift') {
                addGift(item.data);
            } else if (item.type === 'sc') {
                addSuperChat(item.data);
            } else if (item.type === 'guard') {
                addGuard(item.data);
            }
        });
    } catch (e) {
        console.error('加载历史记录失败:', e);
    }
}
