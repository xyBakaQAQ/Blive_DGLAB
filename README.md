# Bilibili 直播弹幕 DG-Lab 控制器

## 免责声明

>本项目仅供学习之用。使用本项目代码所产生的一切后果由使用者自行承担，开发者不承担任何责任。

**重要提示**：
- 请确保遵守所在地区的法律法规
- 请负责任地使用本工具，不要用于非法或有害的目的
- 使用前请充分了解 DG-Lab 设备的相关说明文档
- 本项目与 Bilibili 官方无关，仅为第三方应用

---

这是一个将 Bilibili 直播间互动与 DG-Lab 联动的程序。

## 功能特性

- **弹幕触发**：观众发送弹幕时触发强度脉冲
  - 支持舰长/提督/总督额外加成（可选）
  - 支持限流：X分钟内同一用户最多触发X次
- **礼物系统**：根据金瓜子礼物档位触发不同强度和时长
- **醒目留言**：Super Chat 按价格档位触发
- **上舰联动**：用户开通舰长/提督/总督时触发
- **互动事件**：进房、关注、分享、特别关注等事件触发
- **灵活配置**：通过 YAML 配置文件管理所有参数

## 环境要求

- Python 3.13 及以上版本
- Bilibili （自行获取 SESSDATA）
- [DG-Lab Coyote Game Hub](https://github.com/hyperzlib/DG-Lab-Coyote-Game-Hub)（第三方库，用于控制器通信）

## 依赖项目

本项目依赖以下开源项目：

- **[DG-Lab Coyote Game Hub](https://github.com/hyperzlib/DG-Lab-Coyote-Game-Hub)** - DG-Lab 设备的开源控制中心，提供 HTTP API 接口支持

## 使用

1. 克隆或下载本项目

2. 安装依赖包

    ```sh
    pip install -r requirements.txt
    ```

## 配置

请在 `config.yaml` 中填写直播间 ID、SESSDATA、以及 DG‑Lab 控制器地址等必要信息。

> **注意**：SESSDATA 用于获取用户名，若未填写则无法获取用户信息

> 不要将含有真实 SESSDATA 的配置文件上传到公开仓库

### 主要配置项

#### 弹幕配置
```yaml
danmaku:
  enabled: true          # 是否启用弹幕触发
  strength_add: 1        # 触发强度
  duration: "30s"        # 持续时间
  rate_limit:
    enabled: true        # 是否启用限流
    time_window: "1m"    # 时间窗口（1分钟内）
    max_count: 5         # 同一个人最多触发5次
  guard_bonus:           # 舰长弹幕加成
    enabled: false       # 舰长加成总开关
```

#### 礼物档位
```yaml
gift:
  enabled: true
  tiers:
    - min_price: 0.1     # 最低价格（元）
      strength_add: 5    # 触发强度
      duration: "2m"     # 持续时间
```

#### 其他事件
- **互动事件**：进房、关注、分享等
- **醒目留言**：按价格档位配置
- **上舰**：按舰长等级配置

详细配置请参考 `config.yaml` 文件中的注释说明。


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


## 许可证

本项目采用 MIT License。详见 [LICENSE](./LICENSE) 文件。

## 致谢

感谢以下项目的支持与贡献：

- **[blivedm](https://github.com/xfgryujk/blivedm)** - Bilibili 直播弹幕库，提供直播间事件监听功能
- **[DG-Lab Coyote Game Hub](https://github.com/hyperzlib/DG-Lab-Coyote-Game-Hub)** - DG-Lab 设备的开源控制中心，提供 HTTP API 接口支持

## 反馈与贡献

欢迎提交 Issue 和 Pull Request！