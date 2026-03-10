const danmakuLogsDiv = document.getElementById('danmaku-logs');
const dglabLogsDiv = document.getElementById('dglab-logs');
let ws = null;

function connectWebSocket() {
    ws = new WebSocket(`ws://${location.host}/ws`);
    
    ws.onopen = () => {
        console.log('WebSocket 已连接');
        document.getElementById('status').textContent = '运行中';
        document.getElementById('status').className = 'status online';
    };
    
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'log') {
            const logType = msg.log_type || 'all';
            if (logType === 'danmaku') {
                addLog(danmakuLogsDiv, msg.data);
            } else if (logType === 'dglab') {
                addLog(dglabLogsDiv, msg.data);
            } else {
                // 其他日志不显示在首页
            }
        }
    };
    
    ws.onclose = () => {
        console.log('WebSocket 已断开，3秒后重连...');
        document.getElementById('status').textContent = '断开连接';
        document.getElementById('status').className = 'status offline';
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
    };
}

function addLog(container, log) {
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `<span class="log-time">[${log.time}]</span> <span class="log-${log.level}">[${log.level}]</span> <span class="log-message">${escapeHtml(log.message)}</span>`;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
    
    // 限制日志条数
    while (container.children.length > 100) {
        container.removeChild(container.firstChild);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadConfig() {
    try {
        const resp = await fetch('/api/config');
        const config = await resp.json();
        document.getElementById('room-id').textContent = config.bilibili.room_id;
        document.getElementById('controller-id').textContent = config.dglab.controller_id;
    } catch (e) {
        console.error('加载配置失败:', e);
    }
}

async function loadLogs() {
    try {
        // 加载弹幕日志
        const danmakuResp = await fetch('/api/logs?type=danmaku');
        const danmakuLogs = await danmakuResp.json();
        danmakuLogs.forEach(log => addLog(danmakuLogsDiv, log));
        
        // 加载郊狼日志
        const dglabResp = await fetch('/api/logs?type=dglab');
        const dglabLogs = await dglabResp.json();
        dglabLogs.forEach(log => addLog(dglabLogsDiv, log));
    } catch (e) {
        console.error('加载日志失败:', e);
    }
}

// 初始化
loadConfig();
loadLogs();
connectWebSocket();

// OBS 弹窗功能
function showObsModal() {
    const modal = document.getElementById('obs-modal');
    const urlInput = document.getElementById('obs-url');
    const obsUrl = `${window.location.protocol}//${window.location.host}/obs.html`;
    urlInput.value = obsUrl;
    modal.style.display = 'block';
}

function closeObsModal() {
    const modal = document.getElementById('obs-modal');
    modal.style.display = 'none';
}

async function copyObsUrl() {
    const urlInput = document.getElementById('obs-url');
    await navigator.clipboard.writeText(urlInput.value);
}

// 点击弹窗外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('obs-modal');
    if (event.target === modal) {
        closeObsModal();
    }
}
