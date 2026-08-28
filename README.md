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
  <img alt="Release" src="https://img.shields.io/badge/version-v0.2.5-23ADE5"/>
</p>

Dailykyi 是一个可视化的 B 站每日任务自动化工具。只需完成一次扫码登录，它会按你设定的策略自动完成 **投币 / 观看 / 分享 / 直播签到 / 银瓜子兑换** 等任务，并把执行结果推送到你的手机上。

前端基于 Vue 3 + Element Plus（22 & 33 双主题），后端基于 FastAPI + SQLite，所有服务通过 Docker Compose 一键拉起，**5 分钟即可部署完成**。

---

## ✨ 功能特性

| 分类 | 功能 |
|---|---|
| 🎨 UI | 22 粉 / 33 蓝 双主题一键切换 · 侧边栏 2233娘轮播图 |
| 🔐 账号 | 管理员密码登录 · 首次强制改密 · B 站扫码登录自动存 Cookie |
| 🪄 任务 | 投币策略（数量 / 是否给自己 / 按优先分区）· 观看时长（300/310/350s 满足 5 分钟规则）· 分享 · 直播签到 · 银瓜子兑换硬币 |
| ⏰ 调度 | 可视化配置每日执行时间 · Cron 定时触发 · 支持手动立即执行 |
| 📊 仪表盘 | 多账号状态一览 · 今日经验增长（基于经验快照 24h 前后对比，不再依赖任务上报数值）· LV6 预估达成日期 · 任务成功 / 失败统计 |
| 📜 日志 | 结构化任务列表 · 实时日志流 SSE 推送 · 按账号 / 级别过滤 · 本地时区显示 |
| 🔔 推送 | Server酱 微信公众号推送 · Bark iOS 推送（失败提醒 / 每日报告）· 每日汇总按用户已启用任务数触发（不再固定三任务判定） |
| 🐳 部署 | Docker Compose 三容器编排（nginx + frontend-static + backend + sqlite持久化）· 容器时区 Asia/Shanghai 与本机一致 |
| 🚀 升级 | 右上角快捷版本检测徽章（4h 缓存）· 一键升级 · GitHub Releases 自动检查 |

### v0.2.5 新特性

- **project.md 不再跟随开源仓库发布**：已加入 `.gitignore` 并从 git 追踪中移除（本地开发自用文档保留）
- **术语修正**：README 与前端源码中的「吉祥物」统一改为官方称呼「2233娘」（含 UI alt 属性与工具说明）
- **修复系统设置一键升级报错「升级脚本不存在: /scripts/update.sh」**（从 0.2.0/0.2.1 升级常见问题）
  - 后端升级服务现在按 5 条路径依次查找脚本，报错时给出「已搜索的路径 + 三种解决方法」
  - Docker 生产 compose 默认把项目根 bind-mount 进容器 `/host`，后端容器内即可执行宿主机的升级流程
  - Dockerfile 默认把 `scripts/` 和 `docker-compose.yml` 打进后端镜像兜底；容器内预装 bash + docker CLI
  - `scripts/update.sh` 现在同时支持「源码模式 (git pull→build→up -d)」和「纯镜像模式 (pull→up -d)」
- **真正的 Docker 一键部署脚本**：`scripts/install-docker.sh`，支持 `curl | bash` 一行部署，**不需要 `git clone` / 不需要 npm / 不需要 python**（详见方式一·A 一键脚本）
- **部署文档按你要求重写**：本地部署 / Docker 分批手动部署 / Docker 一键脚本部署 三种形态独立小节

### v0.2.1 新特性

- **经验日志模块**：侧边栏新增「经验日志」页面，按日聚合展示经验变化，来源区分 Dailykyi 自动任务与站外其他 App，并以不同颜色标识
- **版本与升级卡片改版**：由横版改为长方形卡片，与其余 5 个卡片尺寸统一；22 & 33 头像比例调整为 3:2（1.5:1）以完整显示内容
- **调试与诊断卡片改版**：同步改为长方形卡片；「发送一次失败通知测试」「检查更新」两个按钮下移到标题+说明文字下方，和其它卡片保存按钮对齐
- **面板版本检测「问号」问题修复**：健康检查 /api/v1/health 不再返回异常值，版本号正常显示

### v0.2.0 新特性

- **经验快照机制**：每 6 小时自动记录一次账号经验 + 任务执行后主动记录一次，前后对比真实经验 delta，杜绝任务虚报 +5 的历史 bug
- **LV6 预估**：基于近 7 天经验快照日均计算到达 LV6 还需天数与达成日期
- **每日汇总按需触发**：用户启用的任务全部执行完毕后才发汇总通知（不再"三任务固定判定"）
- **任务经验真实判定**：投币/观看/分享不再依赖 B 站接口 bool 状态，改用经验快照 delta 准确判断是否真获得经验（可识别"别处设备已完成"场景）
- **日志时间本地化**：修复容器时区导致日志显示晚 8 小时的问题
- **快捷版本徽章**：右上角仅在有新版本时显示，4h 缓存避免频繁打 GitHub API

---

## 🚀 快速开始

> **日常升级（所有部署方式通用命令）**：
> ```bash
> bash scripts/update.sh              # 源码部署：git pull → 构建前端 → 重建后端 → up -d
> bash scripts/update.sh --image-only # 一键脚本部署（无源码）：拉最新镜像 + 重启容器
> ```
> 也可以在面板「**系统设置 → 版本与升级**」点「检查更新 / 一键升级」按钮，效果与命令相同。

---

### 方式一 · A：Docker 一键脚本部署（**最推荐·真·一行**）

**不需要 `git clone`，不需要安装 Node/Python，仅需服务器有 Docker**：
- 自动拉最新官方镜像
- 自动生成 `/opt/dailykyi` 目录结构（compose / .env / data / logs / scripts）
- 自动生成随机 **SECRET_KEY**，默认凭证 + 端口可通过传参覆盖
- 自动健康检查，成功后直接打印访问地址与常用命令

```bash
# 最简单：默认端口 23333 / 默认账号 2233 / 默认密码 tv23333
bash <(curl -sSL https://raw.githubusercontent.com/breezets/Dailykyi/main/scripts/install-docker.sh)
```

常用参数（脚本设计成 `curl … | bash -s -- --port …` 这种也能跑）：

```bash
# 自定义公网端口 + 默认账号密码
bash <(curl -sSL https://raw.githubusercontent.com/breezets/Dailykyi/main/scripts/install-docker.sh) \
  --port 8080 --username admin --password '请改成你自己的强密码'

# 有公网域名：启动后直接显示 https 地址
bash <(curl -sSL https://raw.githubusercontent.com/breezets/Dailykyi/main/scripts/install-docker.sh) \
  --domain dailykyi.example.com --port 443

# 升级已部署的 Dailykyi（保留 .env / 数据 / 日志，仅拉最新镜像并重启）
bash <(curl -sSL https://raw.githubusercontent.com/breezets/Dailykyi/main/scripts/install-docker.sh) --upgrade

# 卸载（默认保留数据卷；加 --delete-data 则一并删除数据库与配置）
bash <(curl -sSL https://raw.githubusercontent.com/breezets/Dailykyi/main/scripts/install-docker.sh) --uninstall
```

> 若你的服务器访问 GitHub raw 较慢，也可以先把脚本内容 `curl -o install.sh URL` 存下再运行 `bash install.sh`，功能完全一样。

启动完成后访问：**http://服务器公网IP:23333**

| 默认项 | 值 |
|---|---|
| 默认账号 | `2233` |
| 默认密码 | `tv23333` |

> ⚠️ 首次登录会**强制修改默认密码**。部署到公网服务器时务必修改默认密码或使用 `--password` 参数覆盖。

---

### 方式一 · B：Docker 分批手动部署（要改源码 / 走自建镜像时用）

> 环境要求：Docker ≥ 20.10，Docker Compose ≥ 2.0，Node ≥ 18（需要构建前端静态文件时）

```bash
# ① 克隆仓库
git clone https://github.com/breezets/Dailykyi.git
cd Dailykyi

# ② 复制环境变量模板（必须修改 SECRET_KEY / 默认密码）
cp .env.example .env

# ③ 构建前端静态资源（交给 nginx 容器提供）
cd frontend && npm install && npm run build && cd ..

# ④ 三容器编排启动：nginx / backend / sqlite 数据卷
docker compose up -d
```

手动升级（保留数据 / 日志）：

```bash
git pull --ff-only origin main        # 或：main 改成你的分支
cd frontend && npm install && npm run build && cd ..
docker compose build backend
docker compose up -d
```

---

### 方式二：本地开发部署（前后端热重载，贡献代码用）

```bash
# Docker Compose dev：Vite HMR 前端 + FastAPI --reload 后端 + 本地 SQLite
docker compose -f docker-compose.dev.yml up
```

- 前端开发服务器（Vite HMR）：**http://localhost:23333**（端口与生产部署统一）
- 后端 API：**http://localhost:8000**
- Swagger 文档：**http://localhost:8000/docs**
- 前端 Vite 已配置 `/api` → 后端代理，直接联调无需处理跨域

也可以在宿主机分两次跑（非 docker）：

```bash
# 终端 1（后端）
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000

# 终端 2（前端）
cd frontend && npm install && npm run dev
```

---

## 🔧 关于一键升级常见问题（从 v0.2.0 / v0.2.1 升级必读）

**Q：点击「一键升级」后报错 升级脚本不存在: /scripts/update.sh？**
A：这是老版本 compose **没有把宿主机项目根挂载进容器**导致。解决方法（任选其一，推荐第一条）：
1. 使用 v0.2.5 的 docker-compose.yml 重启一次后端：
   ```bash
   curl -sSLo docker-compose.yml https://raw.githubusercontent.com/breezets/Dailykyi/main/docker-compose.yml
   docker compose up -d backend
   ```
   然后在系统设置里再点一键升级即可。
2. 或者：直接在服务器上执行升级命令（和面板效果等价）：
   ```bash
   bash <(curl -sSL https://raw.githubusercontent.com/breezets/Dailykyi/main/scripts/install-docker.sh) --upgrade
   ```
3. 或者：先从界面外升级到 v0.2.5 后，后面的所有小版本都能在面板里一键升级完成。

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

## 🎨 2233娘图片替换

Dailykyi 预置了 22 & 33 的角色图位，直接覆盖同名文件即可生效，**无需重新构建前端**：

```
frontend/public/mascots/
├── 01.png ~ 09.png            ← 1:1 方图，侧边栏轮播用
└── homephoto/
    ├── home-01.png ~ home-18.png/jpg/webp   ← 首页横幅图（任意比例自动适配）
```

> 建议把图片压缩到 **400×400（方图）/ 800px 宽（横幅）** 以内，提升页面加载速度。

---

## 📂 项目结构

```
Dailykyi/
├── backend/                 # FastAPI 后端 (Python)
├── frontend/                # Vue 3 前端 (Vite / TS / Element Plus)
├── docker/                  # Nginx 反向代理 + 前端静态资源托管
├── scripts/init_db.py       # 数据库初始化脚本
├── docker-compose.yml       # 生产：nginx + backend + SQLite 数据卷
├── docker-compose.dev.yml   # 开发：前后端热重载
└── .env.example             # 环境变量模板（复制为 .env 修改）
```

---

## ⚠️ 注意事项

1. **扫码登录回调**：B 站 APP 扫码后的回调需要能从手机访问面板地址。本地 `localhost` 可能回调失败，建议用**局域网 IP**（如 `http://192.168.x.x:23333`）或直接部署到公网服务器后再扫码。
2. **查看运行日志**：调度器与任务执行状态可通过后端日志查看：
   ```bash
   docker logs -f dailykyi-backend
   ```
3. **数据持久化**：SQLite DB 与运行日志保存在 docker named volume 中，`docker compose down` **不会**删除数据（加 `-v` 才会，慎用）。

---

## 🛡️ 免责声明

本项目仅供学习交流使用。使用自动化工具操作 B 站账号可能违反平台相关条款，存在封号风险，请自行评估并承担相应后果。

---

## 📄 License

MIT —— 详见 [LICENSE](./LICENSE)
