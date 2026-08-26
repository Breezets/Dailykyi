# Dailykyi · 每日姬

<p align="center">
  <strong>B 站每日任务自动化 · 22 & 33 主题管理面板</strong><br>
  投币 / 观看 / 分享 定时调度 · 多账号管理 · 实时日志 · Server酱 推送
</p>

<p align="center">
  <img alt="Vue 3" src="https://img.shields.io/badge/Vue-3.x-4FC08D?logo=vuedotjs&logoColor=white"/>
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white"/>
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-3.x-003B57?logo=sqlite&logoColor=white"/>
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white"/>
  <img alt="License: MIT" src="https://img.shields.io/github/license/breezets/Dailykyi?color=fb7299"/>
  <img alt="Release" src="https://img.shields.io/badge/version-v0.1.1-23ADE5"/>
</p>

Dailykyi 是一个可视化的 B 站每日任务自动化工具。只需完成一次扫码登录，它会按你设定的策略自动完成 **投币 / 观看 / 分享 / 直播签到 / 银瓜子兑换** 等任务，并把执行结果推送到你的手机上。

前端基于 Vue 3 + Element Plus（22 & 33 双主题），后端基于 FastAPI + SQLite，所有服务通过 Docker Compose 一键拉起，**5 分钟即可部署完成**。

---

## ✨ 功能特性

| 分类 | 功能 |
|---|---|
| 🎨 UI | 22 粉 / 33 蓝 双主题一键切换 · 侧边栏吉祥物轮播图 |
| 🔐 账号 | 管理员密码登录 · 首次强制改密 · B 站扫码登录自动存 Cookie |
| 🪄 任务 | 投币策略（数量 / 是否给自己 / 按优先分区）· 观看时长 · 分享 · 直播签到 · 银瓜子兑换硬币 |
| ⏰ 调度 | 可视化配置每日执行时间 · Cron 定时触发 · 支持手动立即执行 |
| 📊 仪表盘 | 多账号状态一览 · 今日经验增长 · 任务成功 / 失败统计 |
| 📜 日志 | 结构化任务列表 · 实时日志流 WebSocket 推送 · 按账号 / 级别过滤 |
| 🔔 推送 | Server酱 微信公众号推送 · Bark iOS 推送（失败提醒 / 每日报告） |
| 🐳 部署 | Docker Compose 三容器编排（nginx + frontend-static + backend + sqlite持久化） |

---

## 🚀 快速开始

### 方式一：Docker 一键部署（推荐）

> 环境要求：Docker ≥ 20.10，Docker Compose ≥ 2.0

```bash
# 1. 克隆仓库
git clone https://github.com/breezets/Dailykyi.git
cd Dailykyi

# 2. 复制环境变量模板（按需修改 SECRET_KEY / DEFAULT_ADMIN_PASSWORD）
cp .env.example .env

# 3. 构建前端静态资源
cd frontend && npm install && npm run build && cd ..

# 4. 一键启动（三容器：nginx / backend / sqlite 数据卷）
docker compose up -d
```

启动完成后访问：**http://localhost:23333**

| 默认项 | 值 |
|---|---|
| 默认账号 | `2233` |
| 默认密码 | `tv23333` |

> ⚠️ 首次登录会**强制修改默认密码**。部署到公网服务器时，把 `localhost` 换成服务器 IP 或域名即可。

---

### 方式二：本地开发调试（前后端热重载）

```bash
docker compose -f docker-compose.dev.yml up
```

- 前端开发服务器（Vite HMR）：http://localhost:3000
- 后端 API（FastAPI --reload）：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 前端 Vite 已配置 `/api` 代理 → `http://localhost:8000`，直接联调无需处理跨域。

---

## ⚙️ 环境变量说明（`.env`）

复制 `.env.example` 为 `.env` 后修改，**不要把真实值写进 `.env.example`**：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `SECRET_KEY` | `change-me-please` | JWT 签名密钥，**生产必须改为随机长字符串** |
| `DEFAULT_ADMIN_USERNAME` | `2233` | 首次启动时自动创建的管理员用户名 |
| `DEFAULT_ADMIN_PASSWORD` | `tv23333` | 首次启动的默认密码，登录后会强制修改 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | 登录 Token 过期时间（分钟，默认 1 天） |
| `BILI_WBI_CACHE_SECONDS` | `600` | B 站 WBI 签名缓存时间 |
| `BACKEND_CORS_ORIGINS` | `*` | 允许跨域的前端域名，正式环境建议收紧 |
| `LOG_LEVEL` | `INFO` | 日志级别（DEBUG / INFO / WARNING / ERROR） |

---

## 🎨 吉祥物图片替换

Dailykyi 预置了 22 & 33 的角色图位，直接覆盖同名文件即可生效，**无需重新构建前端**：

```
frontend/public/mascots/
├── 01.png ~ 09.png            ← 1:1 方图，侧边栏轮播用
└── homephoto/
    ├── home-01.png ~ home-18.png/jpg/webp   ← 首页横幅图（任意比例自动适配）
```

> 建议把图片压缩到 **400×400（方图）/ 800px 宽（横幅）** 以内，提升页面加载速度。

---

## 🧑‍💻 自定义社交链接

网站底部的 B 站 / GitHub / 文档链接在下面这个文件里修改：

👉 `frontend/src/constants/site.ts`

```typescript
export const SITE = {
  version:    'v0.1.1',
  authorName: '你的昵称',                    // 显示为 "B站 · 昵称"
  slogan:     '22 & 33 陪你做每日任务~',
  copyright:  '© 2026 Dailykyi',
  docs:       'https://你的文档地址',         // 使用文档 / Wiki
  github:     'https://github.com/你/Dailykyi', // 仓库地址
  bilibili:   'https://space.bilibili.com/你的UID', // B 站空间
  license:    'MIT License',
};
```

改完后重新构建前端：`cd frontend && npm run build` 并重启 nginx 容器即可生效。

---

## 📂 项目结构

```
Dailykyi/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── routers/         # auth / accounts / tasks / logs / system / dashboard
│   │   ├── services/        # bili_api + WBI签名 / scheduler / notify / task_handlers
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   └── schemas/         # Pydantic 请求/响应模型
│   ├── alembic/             # 数据库迁移
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Vue 3 + Vite + TS + Element Plus
│   ├── src/
│   │   ├── views/           # Dashboard / TaskConfig / AccountManage / LogViewer / SystemSettings / Login
│   │   ├── components/      # KyiSidebar / KyiHeader / KyiCard / KyiQrModal / KyiThemeSwitch / KyiTimeline
│   │   ├── stores/          # Pinia：auth、theme
│   │   └── constants/site.ts
│   └── public/mascots/      # 22 & 33 角色图位
├── docker/                  # Nginx 容器（反向代理 + 托管前端静态资源）
│   ├── Dockerfile
│   └── nginx.conf
├── scripts/init_db.py       # 单独初始化 DB 的脚本
├── docker-compose.yml       # 生产：nginx + backend + SQLite 数据卷
├── docker-compose.dev.yml   # 开发：前后端热重载
├── .env.example             # 环境变量模板（请复制为 .env）
├── .gitignore
├── .gitattributes
├── LICENSE                  # MIT
└── README.md
```

---

## ⚠️ 注意事项

1. **扫码登录回调**：B 站 APP 扫码后的回调需要能从手机访问面板地址。本地 `localhost` 可能回调失败，建议用**局域网 IP**（如 `http://192.168.x.x:23333`）或直接部署到公网服务器后再扫码。
2. **任务调度调试**：调度器运行状态可通过后端日志查看：
   ```bash
   docker logs -f dailykyi-backend
   ```
3. **数据库迁移**：ORM 模型改动后需执行 Alembic 迁移：
   ```bash
   docker exec dailykyi-backend alembic revision --autogenerate -m "xxx"
   docker exec dailykyi-backend alembic upgrade head
   ```
4. **数据持久化**：SQLite DB 与运行日志分别保存在 docker named volume `dailykyi_db-data` 和 `dailykyi_logs` 中，`docker compose down` **不会**删除它们（加 `-v` 才会，慎用）。

---

## 🛡️ 免责声明

本项目仅供学习交流使用。使用自动化工具操作 B 站账号可能违反平台相关条款，存在封号风险，请自行评估并承担相应后果。

---

## 📄 License

MIT —— 详见 [LICENSE](./LICENSE)
