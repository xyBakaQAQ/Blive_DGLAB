let currentConfig = null;

async function loadConfig() {
    try {
        const resp = await fetch('/api/config/full');
        currentConfig = await resp.json();
        populateForm(currentConfig);
    } catch (e) {
        showMessage('加载配置失败: ' + e.message, 'error');
    }
}

function populateForm(config) {
    // Bilibili
    document.getElementById('room-id').value = config.bilibili.room_id || '';
    document.getElementById('sessdata').value = config.bilibili.sessdata || '';
    
    // DG-Lab
    document.getElementById('dglab-enabled').checked = config.dglab.enabled !== false;
    document.getElementById('controller-url').value = config.dglab.controller_url || '';
    document.getElementById('controller-id').value = config.dglab.controller_id || '';
    
    // WebUI
    const webui = config.webui || {};
    document.getElementById('webui-host').value = webui.host || '0.0.0.0';
    document.getElementById('webui-port').value = webui.port || 8080;
    
    // 弹幕
    document.getElementById('danmaku-enabled').checked = config.danmaku.enabled;
    document.getElementById('danmaku-strength').value = config.danmaku.strength_add;
    document.getElementById('danmaku-duration').value = config.danmaku.duration;
    
    // 限流
    const rateLimit = config.danmaku.rate_limit || {};
    document.getElementById('rate-limit-enabled').checked = rateLimit.enabled;
    document.getElementById('rate-limit-window').value = rateLimit.time_window || '1m';
    document.getElementById('rate-limit-count').value = rateLimit.max_count || 5;
    
    // 礼物
    document.getElementById('gift-enabled').checked = config.gift.enabled;
    renderTiers('gift', config.gift.tiers);
    
    // SC
    document.getElementById('sc-enabled').checked = config.super_chat.enabled;
    renderTiers('sc', config.super_chat.tiers);
    
    // 上舰
    document.getElementById('guard-enabled').checked = config.guard.enabled;
    const guardLevels = config.guard.levels || {};
    if (guardLevels[3]) {
        document.getElementById('guard-3-strength').value = guardLevels[3].strength_add;
        document.getElementById('guard-3-duration').value = guardLevels[3].duration;
    }
    if (guardLevels[2]) {
        document.getElementById('guard-2-strength').value = guardLevels[2].strength_add;
        document.getElementById('guard-2-duration').value = guardLevels[2].duration;
    }
    if (guardLevels[1]) {
        document.getElementById('guard-1-strength').value = guardLevels[1].strength_add;
        document.getElementById('guard-1-duration').value = guardLevels[1].duration;
    }
    
    // 互动
    const interact = config.interact || {};
    ['enter', 'follow', 'share', 'special_follow'].forEach(key => {
        const cfg = interact[key] || {};
        const enabled = document.getElementById(`interact-${key.replace('_', '-')}-enabled`);
        const strength = document.getElementById(`interact-${key.replace('_', '-')}-strength`);
        const duration = document.getElementById(`interact-${key.replace('_', '-')}-duration`);
        if (enabled) enabled.checked = cfg.enabled || false;
        if (strength) strength.value = cfg.strength_add || '';
        if (duration) duration.value = cfg.duration || '';
    });
}

function renderTiers(type, tiers) {
    const container = document.getElementById(`${type}-tiers`);
    container.innerHTML = '';
    
    tiers.forEach((tier, index) => {
        const div = document.createElement('div');
        div.className = 'tier-item';
        div.innerHTML = `
            <input type="number" placeholder="最低价格" value="${tier.min_price}" data-field="min_price">
            <input type="number" placeholder="强度" value="${tier.strength_add}" data-field="strength_add">
            <input type="text" placeholder="持续时间" value="${tier.duration}" data-field="duration">
            <button class="btn-remove" onclick="removeTier('${type}', ${index})">删除</button>
        `;
        container.appendChild(div);
    });
}

function addGiftTier() {
    if (!currentConfig.gift.tiers) currentConfig.gift.tiers = [];
    currentConfig.gift.tiers.push({ min_price: 1, strength_add: 5, duration: '2m' });
    renderTiers('gift', currentConfig.gift.tiers);
}

function addSCTier() {
    if (!currentConfig.super_chat.tiers) currentConfig.super_chat.tiers = [];
    currentConfig.super_chat.tiers.push({ min_price: 30, strength_add: 15, duration: '10m' });
    renderTiers('sc', currentConfig.super_chat.tiers);
}

function removeTier(type, index) {
    const key = type === 'gift' ? 'gift' : 'super_chat';
    currentConfig[key].tiers.splice(index, 1);
    renderTiers(type, currentConfig[key].tiers);
}

function collectTiers(type) {
    const container = document.getElementById(`${type}-tiers`);
    const items = container.querySelectorAll('.tier-item');
    const tiers = [];
    
    items.forEach(item => {
        const inputs = item.querySelectorAll('input');
        const tier = {};
        inputs.forEach(input => {
            const field = input.dataset.field;
            let value = input.value;
            if (field === 'min_price' || field === 'strength_add') {
                value = parseFloat(value);
            }
            tier[field] = value;
        });
        tiers.push(tier);
    });
    
    return tiers;
}

async function saveConfig() {
    try {
        const config = {
            bilibili: {
                room_id: parseInt(document.getElementById('room-id').value),
                sessdata: document.getElementById('sessdata').value
            },
            dglab: {
                enabled: document.getElementById('dglab-enabled').checked,
                controller_url: document.getElementById('controller-url').value,
                controller_id: document.getElementById('controller-id').value
            },
            webui: {
                host: document.getElementById('webui-host').value,
                port: parseInt(document.getElementById('webui-port').value)
            },
            danmaku: {
                enabled: document.getElementById('danmaku-enabled').checked,
                strength_add: parseInt(document.getElementById('danmaku-strength').value),
                duration: document.getElementById('danmaku-duration').value,
                rate_limit: {
                    enabled: document.getElementById('rate-limit-enabled').checked,
                    time_window: document.getElementById('rate-limit-window').value,
                    max_count: parseInt(document.getElementById('rate-limit-count').value)
                },
                guard_bonus: currentConfig.danmaku.guard_bonus || {}
            },
            interact: {
                enter: {
                    enabled: document.getElementById('interact-enter-enabled').checked,
                    strength_add: parseInt(document.getElementById('interact-enter-strength').value) || 1,
                    duration: document.getElementById('interact-enter-duration').value || '30s'
                },
                follow: {
                    enabled: document.getElementById('interact-follow-enabled').checked,
                    strength_add: parseInt(document.getElementById('interact-follow-strength').value) || 3,
                    duration: document.getElementById('interact-follow-duration').value || '30s'
                },
                share: {
                    enabled: document.getElementById('interact-share-enabled').checked,
                    strength_add: parseInt(document.getElementById('interact-share-strength').value) || 2,
                    duration: document.getElementById('interact-share-duration').value || '1m'
                },
                special_follow: {
                    enabled: document.getElementById('interact-special-follow-enabled').checked,
                    strength_add: parseInt(document.getElementById('interact-special-follow-strength').value) || 2,
                    duration: document.getElementById('interact-special-follow-duration').value || '30s'
                }
            },
            gift: {
                enabled: document.getElementById('gift-enabled').checked,
                tiers: collectTiers('gift')
            },
            super_chat: {
                enabled: document.getElementById('sc-enabled').checked,
                tiers: collectTiers('sc')
            },
            guard: {
                enabled: document.getElementById('guard-enabled').checked,
                levels: {
                    3: {
                        strength_add: parseInt(document.getElementById('guard-3-strength').value),
                        duration: document.getElementById('guard-3-duration').value
                    },
                    2: {
                        strength_add: parseInt(document.getElementById('guard-2-strength').value),
                        duration: document.getElementById('guard-2-duration').value
                    },
                    1: {
                        strength_add: parseInt(document.getElementById('guard-1-strength').value),
                        duration: document.getElementById('guard-1-duration').value
                    }
                }
            },
            log: currentConfig.log || { level: 'INFO' }
        };
        
        const resp = await fetch('/api/config/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        const result = await resp.json();
        if (result.success) {
            showMessage(result.message || '配置已保存并生效！', 'success');
            // 重新加载配置以显示最新值
            setTimeout(() => loadConfig(), 500);
        } else {
            showMessage('保存失败: ' + result.error, 'error');
        }
    } catch (e) {
        showMessage('保存失败: ' + e.message, 'error');
    }
}

function showMessage(text, type) {
    const msg = document.getElementById('save-message');
    msg.textContent = text;
    msg.className = type;
    setTimeout(() => {
        msg.style.display = 'none';
    }, 5000);
}

// 初始化
loadConfig();

// 平滑滚动到锚点
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = link.getAttribute('href').substring(1);
        const target = document.getElementById(targetId);
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            // 高亮效果
            target.style.transition = 'box-shadow 0.3s';
            target.style.boxShadow = '0 0 20px rgba(0, 217, 255, 0.5)';
            setTimeout(() => {
                target.style.boxShadow = '';
            }, 1000);
        }
    });
});
