# Bilibili 直播弹幕 DG-Lab 控制器

## ⚠️ 免责声明

>本项目仅供学习之用。使用本项目代码所产生的一切后果由使用者自行承担，开发者不承担任何责任。

**重要提示**：
- 请确保遵守所在地区的法律法规
- 请负责任地使用本工具，不要用于非法或有害的目的
- 使用前请充分了解 DG-Lab 设备的相关说明文档
- 本项目与 Bilibili 官方无关，仅为第三方应用

---

这是一个将 Bilibili 直播间互动与 DG-Lab 联动的程序。

## 功能特性

- **弹幕触发**：观众发送弹幕时触发强度脉冲，支持舰长/提督/总督额外加成
- **礼物系统**：根据金瓜子礼物档位触发不同强度
- **醒目留言**：Super Chat 按价格档位触发
- **上舰联动**：用户开通舰长/提督/总督时触发
- **互动事件**：进房、关注、分享、特别关注等事件触发
- **频率限制**：防止单用户频繁触发
- **灵活配置**：通过 YAML 配置文件管理

## 环境要求

- Python 3.13 及以上版本
- Bilibili （自行获取 SESSDATA）
- [DG-Lab Coyote Game Hub](https://github.com/hyperzlib/DG-Lab-Coyote-Game-Hub)（第三方库，用于控制器通信）

## 依赖项目

本项目依赖以下开源项目：

- **[DG-Lab Coyote Game Hub](https://github.com/hyperzlib/DG-Lab-Coyote-Game-Hub)** - DG-Lab 设备的开源控制中心，提供 HTTP API 接口支持

## 安装

1. 克隆或下载本项目

2. 安装依赖包

    ```sh
    pip install -r requirements.txt
    ```

## 配置

编辑 `config.yaml` 文件配置以下内容：

### 1. Bilibili 账户配置
```yaml
bilibili:
  room_id: 1796101901          # 直播间 ID
  sessdata: "your_sessdata"    # B站 Cookie 中的 SESSDATA
```

### 2. DG-Lab 控制器配置
```yaml
dglab:
  controller_url: "http://127.0.0.1:8920"  # 控制器地址
  controller_id: "all"                      # 设备 ID（all 表示所有设备）
```

### 3. 弹幕触发配置
```yaml
danmaku:
  enabled: true
  strength_add: 3              # 基础强度增加值
  duration: "3s"               # 脉冲持续时间
  rate_limit:
    window: "1m"               # 统计窗口
    max_triggers: 5            # 窗口内单用户最多触发次数
  guard_bonus:                 # 舰长/提督/总督额外加成
    enabled: true
    3: { strength_add: 2, duration: "2s" }  # 舰长
    2: { strength_add: 4, duration: "3s" }  # 提督
    1: { strength_add: 6, duration: "5s" }  # 总督
```

### 4. 互动事件配置
```yaml
interact:
  enter:          # 进入房间
    enabled: false
    strength_add: 1
    duration: "2s"
  follow:         # 关注
    enabled: true
    strength_add: 3
    duration: "3s"
  share:          # 分享
    enabled: true
    strength_add: 4
    duration: "4s"
```

### 5. 礼物档位配置
```yaml
gift:
  enabled: true
  tiers:
    - min_price: 0.1
      strength_add: 5
      duration: "3s"
    # ... 更多档位
```

### 6. 其他配置
- **super_chat**：醒目留言档位
- **guard**：舰长/提督/总督等级配置
- **log**：日志级别和输出选项

## 使用方法

### 运行应用

```sh
python dglab.py
```

### 获取 SESSDATA

#### 方法一：浏览器开发者工具（推荐）

1. 登录 Bilibili
2. 打开浏览器开发者工具（F12）→ 存储/Application
3. 查看 Cookies 中的 `SESSDATA` 值
4. 填入 `config.yaml` 的 `sessdata` 字段

<details>
<summary>方法二：PiliPlus 应用</summary>

1. 下载安装 [PiliPlus](https://github.com/bggRGjQaUbCoE/PiliPlus) 应用
2. 打开 PiliPlus 并登录您的 Bilibili 账户
3. 进入 **设置** → **关于**
4. 找到 **"导入\导出登录信息"**
5. 复制导出的 SESSDATA
6. 填入 `config.yaml` 的 `sessdata` 字段

**优点**：无需手动提取 SESSDATA (?)

</details>

## 时间格式支持

配置文件中的时间值支持以下格式：

- `"30s"` → 30 秒
- `"2m"` → 2 分钟（120 秒）
- `"1m30s"` → 1 分钟 30 秒
- `30` 或 `30.0` → 数字格式（秒）

## 日志输出

应用运行时会输出详细的操作日志，例如：

```
14:30:15 [INFO] 已连接到直播间 1796101901，按 Ctrl+C 退出
14:30:22 [INFO] [弹幕] 用户名：大家好 → +3 / 3s
14:30:25 [INFO] [礼物] 用户名 礼物名 x1（¥10.00）→ +16 / 10s
14:30:30 [INFO] [上舰] 用户名 开通舰长 → +20 / 30s
```

## 文件说明

- `config.yaml` - 应用配置文件
- `dglab.py` - 主程序
- `requirements.txt` - Python 依赖包列表
- `README.md` - 本文件

## 注意事项

⚠️ **安全提示**

- 不要将含有真实 SESSDATA 的配置文件上传到公开仓库
- 建议使用 `.gitignore` 排除 `config.yaml`
- 定期更新 SESSDATA 以保持会话有效

## 故障排除

| 问题 | 解决方案 |
|------|--------|
| 连接超时 | 检查直播间 ID 和网络连接 |
| 403 Forbidden | SESSDATA 已过期，需要重新获取 |
| DG-Lab 请求失败 | 确保控制器地址正确且服务运行中 |
| 事件未触发 | 检查 `config.yaml` 中对应事件的 `enabled` 是否为 `true` |

## 许可证

本项目采用 MIT License。详见 [LICENSE](./LICENSE) 文件。

## 致谢

感谢以下项目的支持与贡献：

- **[blivedm](https://github.com/xfgryujk/blivedm)** - Bilibili 直播弹幕库，提供直播间事件监听功能
- **[DG-Lab Coyote Game Hub](https://github.com/hyperzlib/DG-Lab-Coyote-Game-Hub)** - DG-Lab 设备的开源控制中心，提供 HTTP API 接口支持

## 反馈与贡献

欢迎提交 Issue 和 Pull Request！