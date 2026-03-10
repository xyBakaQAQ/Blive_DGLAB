# Bilibili 直播弹幕 DG-Lab 控制器

## 免责声明

>本项目仅供学习之用。使用本项目代码所产生的一切后果由使用者自行承担，开发者不承担任何责任。

**重要提示**：
- 请确保遵守所在地区的法律法规
- 请负责任地使用本工具，不要用于非法或有害的目的
- 使用前请充分了解 DG-Lab 设备的相关说明文档
- 本项目与 Bilibili 官方无关，仅为第三方应用

---

这是一个将 Bilibili 直播间互动与 DG-Lab 联动的程序，提供 Web UI 管理界面

## 功能特性

### 核心功能
- **弹幕触发**：观众发送弹幕时触发强度脉冲
  - 支持舰长/提督/总督额外加成（可选）
  - 支持限流：X分钟内同一用户最多触发X次
- **礼物系统**：根据金瓜子礼物档位触发不同强度和时长
- **醒目留言**：Super Chat 按价格档位触发
- **上舰联动**：用户开通舰长/提督/总督时触发
- **互动事件**：进房、关注、分享、特别关注等事件触发

### Web UI 功能
- **实时监控**：分别显示弹幕日志和郊狼控制日志
- **在线配置**：通过 Web 界面修改所有配置，保存后立即生效
- **OBS 集成**：提供 OBS 浏览器源页面，实时显示弹幕和郊狼强度信息
- **响应式设计**：侧边栏导航，支持快速定位配置项

## 环境要求

- Python 3.13 及以上版本
- [DG-Lab Coyote Game Hub](https://github.com/hyperzlib/DG-Lab-Coyote-Game-Hub)（第三方库，用于控制器通信）

## 依赖项目

本项目依赖以下开源项目：

- **[blivedm](https://github.com/xfgryujk/blivedm)** - Bilibili 直播弹幕库，提供直播间事件监听功能
- **[DG-Lab Coyote Game Hub](https://github.com/hyperzlib/DG-Lab-Coyote-Game-Hub)** - DG-Lab 设备的开源控制中心，提供 HTTP API 接口支持

## 快速开始

### 1. 安装依赖

```sh
pip install -r requirements.txt
```

### 2. 配置文件

编辑 `config.yaml` 文件，填写必要信息：

```yaml
# Bilibili 直播间配置
bilibili:
  room_id: 1796101901    # 你的直播间 ID
  sessdata: ""           # 从浏览器获取的 SESSDATA

# DG-Lab 控制器配置
dglab:
  enabled: true          # 是否启用郊狼控制器
  controller_url: "http://127.0.0.1:8920"
  controller_id: "all"

# WebUI 配置
webui:
  host: "0.0.0.0"        # 监听地址
  port: 8080             # 监听端口
```

### 3. 运行程序

```sh
python main.py
```

### 4. 访问 Web UI

打开浏览器访问：`http://localhost:8080`

- **首页**：查看实时日志和运行状态
- **配置**：在线修改所有配置项
- **OBS**：获取 OBS 浏览器源链接

## 配置说明

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

</details>

## OBS 集成

### OBS 显示内容

- 从下往上滚动的弹幕
- 用户名和舰长徽章
- 发送时间
- 郊狼强度和持续时间
- 礼物、SC、上舰等特殊消息

## 项目结构

```
.
├── main.py              # 主程序入口
├── bilibili.py          # Bilibili 直播监听模块
├── dglab.py             # DG-Lab 控制器模块
├── web.py               # Web UI 服务器
├── utils.py             # 工具函数（时间解析等）
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖
├── html/                # Web UI 前端文件
│   ├── index.html       # 首页
│   ├── config.html      # 配置页面
│   ├── obs.html         # OBS 页面
│   └── static/          # 静态资源
│       ├── style.css    # 主样式
│       ├── obs.css      # OBS 样式
│       ├── app.js       # 首页脚本
│       ├── config.js    # 配置页脚本
│       └── obs.js       # OBS 脚本
└── blivedm/             # Bilibili 直播弹幕库
```

## 常见问题

### 配置修改后需要重启吗？

大部分配置（弹幕、礼物、SC、上舰等）保存后立即生效，无需重启。但以下配置需要重启：
- WebUI 的 host 和 port
- Bilibili 的 room_id 和 sessdata

### 如何禁用郊狼控制？

在配置页面取消勾选 **启用郊狼控制器**，或在 `config.yaml` 中设置：
```yaml
dglab:
  enabled: false
```

### OBS 页面刷新后没有历史弹幕？

OBS 页面会自动加载最近 50 条弹幕历史记录。如果没有显示，请检查：
1. 程序是否正常运行
2. WebSocket 连接是否正常（查看浏览器控制台）

## 许可证

本项目采用 MIT License。详见 [LICENSE](./LICENSE) 文件。

## 致谢

感谢以下项目的支持与贡献：

- **[blivedm](https://github.com/xfgryujk/blivedm)** - Bilibili 直播弹幕库
- **[DG-Lab Coyote Game Hub](https://github.com/hyperzlib/DG-Lab-Coyote-Game-Hub)** - DG-Lab 设备控制中心

## 反馈与贡献

欢迎提交 Issue 和 Pull Request！
