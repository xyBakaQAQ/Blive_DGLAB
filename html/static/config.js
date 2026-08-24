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

    const viewer = config.viewer_rules || {};
    document.getElementById('viewer-rules-enabled').checked = viewer.enabled === true;
    document.getElementById('viewer-default-action').value = viewer.default?.action || 'add';
    document.getElementById('viewer-default-strength').value = viewer.default?.strength || 1;
    document.getElementById('viewer-default-duration').value = viewer.default?.duration || '30s';
    document.getElementById('viewer-users-json').value = JSON.stringify(viewer.special_users || [], null, 2);
    document.getElementById('viewer-keywords-json').value = JSON.stringify(viewer.keywords || [], null, 2);
    
    // 礼物
    document.getElementById('gift-enabled').checked = config.gift.enabled;
    renderTiers('gift', config.gift.tiers);
    renderGiftRules(config.gift.rules || []);
    
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

function renderGiftRules(rules) {
    const container = document.getElementById('gift-rules');
    container.innerHTML = '';
    rules.forEach((rule, index) => {
        const div = document.createElement('div');
        div.className = 'gift-rule-item';
        div.innerHTML = `
            <div class="gift-rule-head">
                <label class="checkbox-label"><input type="checkbox" data-field="enabled" ${rule.enabled !== false ? 'checked' : ''}> 启用规则</label>
                <span class="rule-index">规则 ${index + 1}</span>
                <button class="btn-remove" onclick="removeGiftRule(${index})">删除</button>
            </div>
            <div class="gift-rule-grid">
                <label>礼物名称
                    <input type="text" placeholder="留空表示金额规则" value="${escapeHtml(rule.gift_name || '')}" data-field="gift_name">
                </label>
                <label>名称匹配
                    <select data-field="match_type">
                        <option value="exact" ${rule.match_type !== 'contains' ? 'selected' : ''}>完全相同</option>
                        <option value="contains" ${rule.match_type === 'contains' ? 'selected' : ''}>包含文字</option>
                    </select>
                </label>
                <label>价格模式
                    <select data-field="price_mode">
                        <option value="total" ${rule.price_mode !== 'unit' ? 'selected' : ''}>本次总额</option>
                        <option value="unit" ${rule.price_mode === 'unit' ? 'selected' : ''}>单个礼物</option>
                    </select>
                </label>
                <label>最低金额
                    <input type="number" min="0" step="0.01" placeholder="可空" value="${rule.min_price ?? ''}" data-field="min_price">
                </label>
                <label>最高金额
                    <input type="number" min="0" step="0.01" placeholder="可空" value="${rule.max_price ?? ''}" data-field="max_price">
                </label>
                <label>强度增加
                    <input type="number" min="1" max="100" value="${rule.strength_add ?? 1}" data-field="strength_add">
                </label>
                <label>持续时间
                    <input type="text" placeholder="30s / 1m" value="${escapeHtml(rule.duration || '30s')}" data-field="duration">
                </label>
            </div>
        `;
        container.appendChild(div);
    });
}

function addGiftRule() {
    if (!currentConfig.gift.rules) currentConfig.gift.rules = [];
    currentConfig.gift.rules.push({ enabled: true, gift_name: '', match_type: 'exact', price_mode: 'total', min_price: '', max_price: '', strength_add: 5, duration: '30s' });
    renderGiftRules(currentConfig.gift.rules);
}

function removeGiftRule(index) {
    currentConfig.gift.rules.splice(index, 1);
    renderGiftRules(currentConfig.gift.rules);
}

function collectGiftRules() {
    return Array.from(document.querySelectorAll('#gift-rules .tier-item')).map(item => {
        const rule = {};
        item.querySelectorAll('input, select').forEach(input => {
            rule[input.dataset.field] = input.type === 'checkbox' ? input.checked : input.value.trim();
        });
        if (rule.min_price !== '') rule.min_price = parseFloat(rule.min_price);
        else delete rule.min_price;
        if (rule.max_price !== '') rule.max_price = parseFloat(rule.max_price);
        else delete rule.max_price;
        rule.strength_add = parseInt(rule.strength_add, 10);
        return rule;
    }).filter(rule => rule.gift_name || rule.min_price !== undefined || rule.max_price !== undefined);
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
        const parseJsonList = id => {
            const value = document.getElementById(id).value.trim();
            if (!value) return [];
            const parsed = JSON.parse(value);
            if (!Array.isArray(parsed)) throw new Error(`${id} 必须是数组`);
            return parsed;
        };
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
            viewer_rules: {
                enabled: document.getElementById('viewer-rules-enabled').checked,
                default: {
                    enabled: true,
                    action: document.getElementById('viewer-default-action').value,
                    strength: parseInt(document.getElementById('viewer-default-strength').value, 10) || 1,
                    duration: document.getElementById('viewer-default-duration').value || '30s'
                },
                special_users: parseJsonList('viewer-users-json'),
                keywords: parseJsonList('viewer-keywords-json')
            },
            // 远程配置不在客户端前端展示，保存其他配置时原样保留
            remote: currentConfig.remote || {},
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
                rules: collectGiftRules(),
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

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
