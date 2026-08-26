# Dailykyi · 每日姬

<p align="center">
  <strong>Dailykyi —— 22 & 33 的 B 站每日任务小助手</strong><br>
  B 站投币 / 观看 / 分享 自动化调度 · 多账号管理 · 实时日志 · Server酱 推送
</p>

<p align="center">
  <img alt="Vue 3" src="https://img.shields.io/badge/Vue-3.x-4FC08D?logo=vuedotjs&logoColor=white"/>
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white"/>
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-3.x-003B57?logo=sqlite&logoColor=white"/>
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white"/>
  <img alt="License: MIT" src="https://img.shields.io/github/license/breezets/Dailykyi?color=fb7299"/>
  <img alt="Release" src="https://img.shields.io/badge/version-v0.1.1-23ADE5"/>
</p>

Dailykyi 是一个基于 FastAPI + Vue3 的 B 站每日任务自动化工具，支持投币、观看、分享等任务的定时调度、多账号管理、日志监控和 Server酱 移动端推送。

## 功能特性

- 🎀 22 & 33 双主题切换（粉 / 蓝）
- 🔐 管理员账号登录，首次登录强制修改默认密码
- 📱 B 站扫码登录，自动保存 Cookie
- ⚙️ 可视化任务配置：投币策略、观看时长、定时调度
- 📊 仪表盘：账号状态、今日经验、任务统计
- 📜 执行日志与实时日志流
- 🔔 Bark / Server 酱推送通知
- 🐳 Docker 一键部署

## 系统要求

- Docker >= 20.10
- Docker Compose >= 2.0

## 生产部署

```bash
cp .env.example .env                     # 修改密钥与默认密码
cd frontend && npm install && npm run build && cd ..
docker-compose up -d                     # 构建并启动服务
# 打开浏览器访问 http://localhost:23333
```

> 注：原需求端口 `233333` 超出 TCP 端口范围，已调整为合法端口 `23333`。

首次启动后，使用默认账号 `2233` / 密码 `tv23333` 登录，并按提示修改密码。

> 部署到服务器时，请将 `localhost` 替换为服务器 IP 或域名。

## 本地测试步骤

1. 克隆仓库
   ```bash
   git clone <repo-url>
   cd Dailykyi
   ```

2. 复制环境变量
   ```bash
   cp .env.example .env
   ```

3. 构建前端并启动服务
   ```bash
   cd frontend && npm install && npm run build && cd ..
   docker-compose up -d
   ```

4. 访问面板
   ```
   http://localhost:23333
   ```

5. 使用默认账号登录
   - 用户名：`2233`
   - 密码：`tv23333`

## 开发调试

使用 `docker-compose.dev.yml` 启动开发模式：

```bash
docker-compose -f docker-compose.dev.yml up
```

- 前端：http://localhost:3000（代码挂载，热重载）
- 后端：http://localhost:8000（代码挂载，`--reload` 自动重启）

前端 Vite 已配置 `/api` 代理到 `http://localhost:8000`，可直接联调。

## 首次初始化数据库

若需要单独初始化数据库表结构，可执行：

```bash
python scripts/init_db.py
```

或在容器内执行：

```bash
docker exec dailykyi-backend python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"
```

## 目录结构

```
Dailykyi/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── services/
│   │   └── ...
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Vue3 前端
│   ├── src/
│   ├── index.html
│   └── package.json
├── docker/                  # Nginx 镜像与配置
│   ├── Dockerfile
│   └── nginx.conf
├── scripts/
│   └── init_db.py           # 数据库初始化脚本
├── data/                    # SQLite 数据目录（运行后生成）
├── logs/                    # 日志目录（运行后生成）
├── docker-compose.yml       # 生产部署
├── docker-compose.dev.yml   # 开发调试
├── .env.example             # 环境变量示例
└── README.md
```

## 本地扫码登录测试说明

B 站扫码登录需要回调到服务器地址。本地使用 `localhost` 时，二维码可正常生成，但 B 站 APP 扫码后的回调可能无法被容器正确接收。

建议：

- 本地先测试 UI 功能、任务配置保存、仪表盘数据展示。
- 使用局域网 IP（如 `192.168.x.x`）代替 `localhost` 进行扫码测试。
- 扫码登录与任务执行建议在服务器部署后测试。

## 任务测试说明

- 本地可正常测试任务配置页面的表单交互。
- 手动触发任务需要有效的 B 站 Cookie，需在完成扫码登录后测试。
- 调度器是否正常运可通过后端日志查看：
  ```bash
  docker logs -f dailykyi-backend
  ```

## 免责声明

本项目仅供学习交流使用。使用自动化工具操作 B 站账号可能存在风险，请自行评估并承担相应后果。

---

## 🛠️ 开源发布前必做（清空敏感数据）

> **如果直接把 Dailykyi 文件夹拖到 GitHub，会把你本地登录过的 B 站 Cookies、密码哈希、Server酱 Key、执行日志等隐私数据一并传上去。**
> 请先做以下 3 步再上传，30 秒搞定。

### 第 1 步：停掉容器 + 删除本地数据库

```bash
# 停容器（同时清掉 docker 生成的数据卷）
docker compose down -v

# 删除后端目录里实际挂载出的 SQLite DB（里面有加密后的账号 Cookie / 任务日志 / 管理员密码哈希）
# Windows PowerShell:
Remove-Item -Recurse -Force backend\data  -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force data            -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force backend\*.db   -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force backend\logs   -ErrorAction SilentlyContinue

# 或 macOS / Linux:
# rm -rf backend/data backend/*.db backend/logs
```

### 第 2 步：删除本地覆盖的环境变量

```bash
# Windows PowerShell
Remove-Item .env -ErrorAction SilentlyContinue

# 或 macOS / Linux:
# rm -f .env
```

> ⚠️ **不要删除 `.env.example`** —— 这是给用户看的模板，里面没有真实值。

### 第 3 步：（可选）删除 mascots 里的图片，换成占位图说明

你的 2233 原创图如果不打算开放授权，建议不要上传。我们在项目内保留 `public/mascots/` 目录作为位置，并在下面提供替换说明即可。README 已经单独有一节讲这个。

做完以上三步，`git status` 应该只显示源码 / 配置 / 图片占位目录，不会出现 `backend/data/*.db` 或 `.env`。

---

## 🚀 上传到 GitHub（完整流程）

```bash
# 1. 进入项目目录
cd Dailykyi

# 2. 初始化 git 仓库（第一次）
git init
git checkout -b main      # 统一使用 main 分支

# 3. （重要）先确认 .gitignore 生效。这条命令应该不列出 *.db / .env / node_modules / .venv
git status

# 4. 配置你的身份（第一次用 git 需要）
git config user.name  "你的 GitHub 用户名"
git config user.email "你的 GitHub 邮箱"

# 5. 第一次提交
git add -A
git commit -m "feat: initial release v0.1.1"

# 6. 去 https://github.com/new 创建一个空仓库，名字叫 Dailykyi
#    勾选 → ❌不要勾选 README / .gitignore / LICENSE（这些已经在本地有了）

# 7. 关联远程仓库并推送
git remote add origin https://github.com/<你的GitHub用户名>/Dailykyi.git
git push -u origin main
```

> 如果你开启了 2FA，会提示输入密码时用 **Personal Access Token (PAT)** 代替。到 https://github.com/settings/tokens 生成一个只勾选 `repo` 权限的 token 即可。

---

## 🎨 吉祥物图片替换（给使用者看）

Dailykyi 预置了 22 & 33 角色图片位，你可以把自己的 2233 日常图放进去（不会随仓库同步，需要自己放）。

```
frontend/public/mascots/
├── 01.png ~ 09.png            ← 1:1 方图（1000×1000），用于侧边栏轮播
└── homephoto/
    ├── home-01.png ~ home-18.* ← 首页横幅图（任意比例都会自动适配）
```

**替换方法**：直接覆盖同名文件，刷新浏览器即可看到新图，无需重新构建。推荐把图缩到 **400×400 / 800×宽** 左右，避免占带宽。

---

## 📁 目录结构（更新版）

```
Dailykyi/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/         # auth / accounts / tasks / logs / system / dashboard
│   │   ├── services/        # bili_api, notify, scheduler, task_handlers
│   │   ├── models/
│   │   ├── schemas/
│   │   └── ...
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Vue3 + Vite + TS + Element Plus
│   ├── src/
│   │   ├── views/           # Dashboard / TaskConfig / AccountManage / LogViewer / SystemSettings
│   │   ├── components/      # KyiSidebar / KyiHeader / KyiCard / KyiQrModal / KyiThemeSwitch
│   │   ├── stores/          # auth, theme
│   │   ├── api/             # account, task, log, system, auth, dashboard
│   │   └── constants/site.ts# 【改这里：你的 B 站/GitHub/博客链接】
│   ├── public/mascots/      # 吉祥物图片位
│   ├── index.html
│   └── package.json
├── docker/                  # Nginx 镜像与配置
│   ├── Dockerfile
│   └── nginx.conf
├── scripts/
│   └── init_db.py           # 数据库初始化脚本
├── docker-compose.yml       # 生产部署
├── docker-compose.dev.yml   # 开发调试
├── .env.example             # 环境变量示例（不要填真实值）
├── .gitignore               # 已屏蔽 DB/.env/node_modules/.venv 等
├── LICENSE                  # MIT
└── README.md
```

## 🧑‍💻 开源社交链接（在网站底部展示）

打开文件 [frontend/src/constants/site.ts](file:///c:/Users/xiaoz/Desktop/Dailykyi/frontend/src/constants/site.ts)，修改里面的：

- `docs`：使用文档地址（你的技术博客 / GitHub Wiki）
- `github`：你的 GitHub 仓库地址
- `bilibili`：B 站空间链接，例如 `https://space.bilibili.com/123456789`
- `authorName`：你的昵称，会显示在"B站 · 昵称"上
- `copyright`、`license`、`version`、`slogan`

改完后执行一次 `cd frontend && npm run build` 并重启 nginx，网站底部就能看到你的社交链接啦。

## License

MIT License —— 详见 [LICENSE](./LICENSE) 文件。
