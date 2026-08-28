# Dailykyi · 每日姬 · 项目技术文档

> **版本**：v0.2.0  
> **最后更新**：2026-08-27  
> **用途**：供新接手的 AI / 开发者快速理解项目全貌，无需通读源码即可开始工作

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [项目目录结构](#3-项目目录结构)
4. [架构设计](#4-架构设计)
5. [后端详细设计](#5-后端详细设计)
   - 5.1 [配置系统](#51-配置系统)
   - 5.2 [数据库设计](#52-数据库设计)
   - 5.3 [认证与安全](#53-认证与安全)
   - 5.4 [路由层](#54-路由层)
   - 5.5 [服务层](#55-服务层)
   - 5.6 [任务处理器](#56-任务处理器)
   - 5.7 [调度器](#57-调度器)
   - 5.8 [通知服务](#58-通知服务)
   - 5.9 [经验快照机制](#59-经验快照机制v020核心)
6. [前端详细设计](#6-前端详细设计)
   - 6.1 [路由与守卫](#61-路由与守卫)
   - 6.2 [状态管理](#62-状态管理)
   - 6.3 [API 封装层](#63-api-封装层)
   - 6.4 [页面视图](#64-页面视图)
   - 6.5 [组件库](#65-组件库)
   - 6.6 [主题系统](#66-主题系统)
7. [关键业务流程](#7-关键业务流程)
8. [部署与运维](#8-部署与运维)
9. [环境变量说明](#9-环境变量说明)
10. [历史决策与注意事项](#10-历史决策与注意事项)
11. [已知问题与未来规划](#11-已知问题与未来规划)

---

## 1. 项目概述

**Dailykyi（每日姬）** 是一个 B 站每日任务自动化工具，提供可视化 Web 管理面板。

**核心功能**：
- 通过 B 站扫码登录绑定账号（自动加密存储 Cookie）
- 定时自动执行：投币 / 观看视频 / 分享视频 / 直播签到 / 银瓜子兑换硬币
- 多账号管理 + 实时日志 + 经验追踪
- Server酱 / Bark 推送通知
- 22 & 33 双主题界面

**设计理念**：
- 5 分钟 Docker 一键部署
- 前后端分离，但打包为单端口服务（nginx 反代）
- 所有 B 站 Cookie 加密存储（Fernet 对称加密）
- 经验记录采用"主动+被动"快照机制，不依赖任务上报数值

---

## 2. 技术栈

### 后端
| 技术 | 版本 | 用途 |
|---|---|---|
| Python | 3.11+ | 运行时 |
| FastAPI | 0.110+ | Web 框架 |
| Uvicorn | - | ASGI 服务器 |
| SQLAlchemy | 2.0+ (async) | ORM |
| aiosqlite | - | SQLite 异步驱动 |
| Alembic | - | 数据库迁移（项目实际用 `Base.metadata.create_all` 建表，alembic 仅保留） |
| Pydantic | 2.0+ | 数据校验 |
| python-jose (JWT) | - | Token 签发与验证 |
| cryptography (Fernet) | - | Cookie 对称加密 |
| httpx | - | 异步 HTTP 客户端（调用 B 站 API） |
| APScheduler | 3.x | 定时任务调度 |
| loguru | - | 结构化日志 |
| passlib[bcrypt] | - | 管理员密码哈希 |

### 前端
| 技术 | 版本 | 用途 |
|---|---|---|
| Vue | 3.x (Composition API) | UI 框架 |
| TypeScript | 5.x | 类型安全 |
| Vite | 4.x | 构建工具 + 开发服务器 |
| Element Plus | 2.x | UI 组件库 |
| Pinia | 2.x | 状态管理 |
| Vue Router | 4.x | 路由 |
| Axios | 1.x | HTTP 客户端 |
| qrcode | 1.x | 二维码生成 |

### 基础设施
| 技术 | 用途 |
|---|---|
| Docker / Docker Compose | 容器化部署 |
| Nginx | 前端静态资源 + 反向代理 |
| SQLite | 数据库（文件持久化，无需额外服务） |

---

## 3. 项目目录结构

```
Dailykyi/
├── backend/                          # 后端 FastAPI 应用
│   ├── alembic/                      # Alembic 迁移（保留，实际用 create_all）
│   │   ├── versions/
│   │   │   └── .gitkeep
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app/
│   │   ├── models/                   # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py           # 模型注册中心（必须导入所有模型）
│   │   │   ├── account.py            # 账号表
│   │   │   ├── task_config.py        # 任务配置表
│   │   │   ├── task_log.py           # 任务执行日志表
│   │   │   ├── coin_record.py        # 投币记录表
│   │   │   ├── exp_snapshot.py       # 经验快照表（v0.2.0 新增）
│   │   │   └── system_config.py      # 系统配置表
│   │   ├── routers/                  # FastAPI 路由
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # /api/v1/auth 认证
│   │   │   ├── accounts.py           # /api/v1/accounts 账号管理
│   │   │   ├── tasks.py              # /api/v1/tasks 任务配置
│   │   │   ├── logs.py               # /api/v1/logs 日志
│   │   │   ├── dashboard.py          # /api/v1/dashboard 仪表盘
│   │   │   ├── system.py             # /api/v1/system 系统设置
│   │   │   └── health.py             # /api/v1/health 健康检查
│   │   ├── schemas/                  # Pydantic 响应模型
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── account.py
│   │   │   └── task.py               # 包含 Dashboard 相关模型
│   │   ├── services/                 # 业务逻辑层
│   │   │   ├── task_handlers/        # 任务处理器（每种任务一个）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py           # 基类 + TaskResult + refresh_exp_snapshot
│   │   │   │   ├── coin.py           # 投币任务
│   │   │   │   ├── watch.py          # 观看任务
│   │   │   │   ├── share.py          # 分享任务
│   │   │   │   ├── login.py          # 登录任务（每日登录经验）
│   │   │   │   ├── live_sign.py      # 直播签到
│   │   │   │   └── silver2coin.py    # 银瓜子兑换硬币
│   │   │   ├── __init__.py
│   │   │   ├── bili_api.py           # B 站 API 客户端（核心）
│   │   │   ├── bili_wbi.py           # WBI 签名（B 站接口签名）
│   │   │   ├── anti_detect.py        # 反风控指纹生成
│   │   │   ├── scheduler.py          # APScheduler 调度器
│   │   │   ├── notify.py             # 通知服务（Server酱 / Bark）
│   │   │   ├── cookie_checker.py     # Cookie 有效性检测
│   │   │   ├── exp_service.py        # 经验计算服务（v0.2.0 新增）
│   │   │   └── upgrade.py            # 版本升级服务
│   │   ├── __init__.py
│   │   ├── config.py                 # 全局配置（Settings）
│   │   ├── database.py               # 数据库引擎 + init_db
│   │   ├── deps.py                   # FastAPI 依赖（认证、Cookie 解密）
│   │   ├── exceptions.py             # 自定义异常 + 处理器注册
│   │   └── main.py                   # 应用入口（lifespan、中间件、路由挂载）
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   └── .gitignore
├── frontend/                         # 前端 Vue 3 应用
│   ├── public/
│   │   └── mascots/                  # 22 & 33 吉祥物图片
│   │       ├── 01.png ~ 09.png       # 侧边栏方图
│   │       ├── homephoto/            # 首页横幅
│   │       └── down/                 # 用户自定义图片
│   │           └── 1.png             # 版本卡片用的 2233 图
│   ├── src/
│   │   ├── api/                      # API 封装层
│   │   │   ├── request.ts            # Axios 实例 + 拦截器
│   │   │   ├── auth.ts
│   │   │   ├── account.ts
│   │   │   ├── task.ts
│   │   │   ├── log.ts
│   │   │   ├── dashboard.ts
│   │   │   └── system.ts
│   │   ├── assets/styles/
│   │   │   ├── variables.css         # CSS 变量定义
│   │   │   ├── theme-22.css          # 22 粉色主题
│   │   │   └── theme-33.css          # 33 蓝色主题
│   │   ├── components/
│   │   │   ├── KyiCard.vue           # 通用卡片
│   │   │   ├── KyiHeader.vue         # 顶部导航栏（含版本检测徽章）
│   │   │   ├── KyiSidebar.vue        # 侧边栏导航
│   │   │   ├── KyiQrModal.vue        # B 站扫码登录弹窗
│   │   │   ├── KyiThemeSwitch.vue    # 主题切换按钮
│   │   │   └── KyiTimeline.vue       # 日志时间轴组件
│   │   ├── constants/
│   │   │   └── site.ts              # 站点常量（版本号、GitHub 地址等）
│   │   ├── router/
│   │   │   └── index.ts             # 路由表 + 守卫
│   │   ├── stores/
│   │   │   ├── auth.ts              # 认证状态
│   │   │   └── theme.ts             # 主题状态
│   │   ├── types/
│   │   │   └── index.ts             # TypeScript 类型定义
│   │   ├── utils/
│   │   │   ├── date.ts              # 日期格式化（naive datetime 字面量解析）
│   │   │   └── mascot.ts            # 吉祥物图片工具
│   │   ├── views/
│   │   │   ├── LoginView.vue        # 登录页
│   │   │   ├── DashboardView.vue    # 首页仪表盘
│   │   │   ├── TaskConfigView.vue   # 任务配置
│   │   │   ├── AccountManageView.vue # 账号管理
│   │   │   ├── LogViewerView.vue    # 日志查看
│   │   │   └── SystemSettingsView.vue # 系统设置
│   │   ├── App.vue                  # 根组件
│   │   ├── env.d.ts
│   │   └── main.ts                  # 应用挂载入口
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── docker/
│   ├── Dockerfile                   # Nginx 容器
│   └── nginx.conf                   # Nginx 配置
├── scripts/
│   ├── init_db.py                   # 数据库初始化脚本
│   ├── install.sh                   # 一键部署脚本
│   └── update.sh                    # 一键升级脚本
├── .env.example                     # 环境变量模板
├── .gitignore
├── .gitattributes
├── LICENSE
├── README.md
├── docker-compose.yml               # 生产环境编排
├── docker-compose.dev.yml           # 开发环境编排
└── project.md                       # 本文档
```

---

## 4. 架构设计

### 4.1 整体架构

```
                    ┌─────────────────────────────────┐
                    │         用户浏览器               │
                    │   http://localhost:23333        │
                    └────────────┬────────────────────┘
                                 │ HTTP
                    ┌────────────▼────────────────────┐
                    │         Nginx (端口 80)          │
                    │  ┌─────────────────────────┐    │
                    │  │ 静态资源 (frontend/dist) │    │
                    │  └─────────────────────────┘    │
                    │  ┌─────────────────────────┐    │
                    │  │ /api/ → backend:8000     │    │
                    │  └─────────────────────────┘    │
                    └────────────┬────────────────────┘
                                 │
                    ┌────────────▼────────────────────┐
                    │    FastAPI Backend (端口 8000)   │
                    │  ┌───────────┐  ┌────────────┐  │
                    │  │ Routers   │→ │ Services   │  │
                    │  └───────────┘  └──────┬─────┘  │
                    │                        │        │
                    │  ┌─────────────────────▼─────┐  │
                    │  │ BiliClient (httpx async)  │  │
                    │  └────────────┬──────────────┘  │
                    │               │                 │
                    │  ┌────────────▼──────────────┐  │
                    │  │ APScheduler (定时任务)     │  │
                    │  └───────────────────────────┘  │
                    └────────────┬────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
    ┌─────────▼──────┐  ┌───────▼───────┐  ┌──────▼──────┐
    │ SQLite (文件)   │  │ B 站 API      │  │ 推送服务    │
    │ /app/data/     │  │ api.bilibili  │  │ Server酱    │
    │ dailykyi.db    │  │ .com          │  │ Bark        │
    └────────────────┘  └───────────────┘  └─────────────┘
```

### 4.2 请求流转

```
浏览器 → Axios (带 JWT) → Nginx (:80) → /api/ 反代 → FastAPI (:8000)
                                                          │
                                          ┌───────────────┼───────────────┐
                                          │               │               │
                                     认证中间件      路由分发       异常处理器
                                          │               │               │
                                      deps.py        routers/*.py    exceptions.py
                                                          │
                                                    services/*.py
                                                          │
                                              ┌───────────┼───────────┐
                                              │           │           │
                                         SQLAlchemy    BiliClient   APScheduler
                                              │           │           │
                                          SQLite     B 站 API     定时任务
```

### 4.3 开发模式 vs 生产模式

| 特性 | 开发模式 (dev) | 生产模式 (prod) |
|---|---|---|
| 编排文件 | `docker-compose.dev.yml` | `docker-compose.yml` |
| 前端 | Vite Dev Server (HMR, 端口 3000→映射 23333) | Nginx 静态资源 (端口 80→映射 23333) |
| 后端 | uvicorn --reload (端口 8000) | uvicorn (端口 8000) |
| 数据库 | SQLite `/app/data/dailykyi.db` | 同左 |
| 代理 | Vite proxy `/api` → `backend-dev:8000` | Nginx proxy `/api` → `backend:8000` |
| 时区 | `TZ=Asia/Hong_Kong` | `TZ=Asia/Shanghai` |
| 热重载 | 前后端均支持 | 不支持 |

---

## 5. 后端详细设计

### 5.1 配置系统

**文件**：`backend/app/config.py`

所有配置通过 Pydantic `BaseSettings` 管理，环境变量前缀 `DAILYKYI_`：

```python
class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "Dailykyi"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = False

    # 安全
    SECRET_KEY: str = "change-me-please"           # JWT 签名 + Fernet 加密密钥派生
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440         # Token 有效期（分钟）

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///data/dailykyi.db"

    # 默认管理员
    DEFAULT_ADMIN_USERNAME: str = "2233"
    DEFAULT_ADMIN_PASSWORD: str = "tv23333"

    # 登录安全
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 10

    # B 站 API
    BILI_WBI_CACHE_SECONDS: int = 600

    # 日志
    LOG_LEVEL: str = "INFO"
```

**关键点**：
- `SECRET_KEY` 同时用于 JWT 签名和 Cookie 加密（Fernet key 派生），**生产必须修改**
- 首次启动时，如果 `system_configs` 表无管理员记录，会用 `DEFAULT_ADMIN_USERNAME/PASSWORD` 自动创建
- 配置覆盖优先级：环境变量 > `.env` 文件 > 代码默认值

### 5.2 数据库设计

**文件**：`backend/app/database.py`

- 异步引擎：`create_async_engine(settings.DATABASE_URL)`
- Session 工厂：`async_sessionmaker(bind=engine, class_=AsyncSession)`
- 请求级依赖：`get_db()` → `async with AsyncSessionLocal() as session: yield session`
- 建表方式：`Base.metadata.create_all(engine)`（不依赖 Alembic）
- 兼容迁移：`init_db()` 会检查已有表是否缺少新字段（如 `cookie_status`），用 `ALTER TABLE` 补充

#### 5.2.1 表结构总览

##### accounts（账号表）
| 字段 | 类型 | 说明 |
|---|---|---|
| uid | BigInteger PK | B 站 UID |
| username | String | B 站用户名 |
| avatar_url | String | 头像 URL |
| level | Integer | 当前等级 |
| current_exp | Integer | 当前经验值 |
| next_level_exp | Integer | 下一级所需经验 |
| coins | Integer | 硬币数量（缓存） |
| cookie_encrypted | Text | 加密后的 Cookie 字符串 |
| cookie_status | String | ok/expired/missing（v0.2.0 兼容迁移字段） |
| cookie_checked_at | DateTime | 上次 Cookie 检测时间 |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

##### task_configs（任务配置表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | 自增 |
| account_uid | BigInteger FK | 关联 accounts.uid |
| task_type | String(32) | coin/watch/share/login/live_sign/silver2coin |
| enabled | Boolean | 是否启用 |
| config | JSON | 任务参数（如投币数量、观看时长等） |
| schedule_mode | String | fixed（定点）/ random（随机时段） |
| schedule_config | JSON | 调度参数（hour/minute 或 window_start/window_end） |
| max_retries | Integer | 最大重试次数 |
| cooldown_minutes | Integer | 冷却时间（分钟） |
| created_at / updated_at | DateTime | 时间戳 |

##### task_logs（任务日志表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | 自增 |
| account_uid | BigInteger FK | 关联 accounts.uid |
| task_type | String(32) | 任务类型 |
| status | String(16) | pending/running/success/failed/skipped |
| message | Text | 结果消息 |
| detail | JSON | 详细信息（B 站返回值、经验状态等） |
| exp_gained | Integer | 获得经验（v0.2.0 起改用快照 delta，此字段仍保留） |
| started_at | DateTime | 开始时间 |
| completed_at | DateTime | 完成时间 |
| created_at | DateTime | 创建时间（`default=datetime.now` 本地时间） |

##### exp_snapshots（经验快照表，v0.2.0 新增）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | 自增 |
| account_uid | BigInteger FK | 关联 accounts.uid |
| exp | Integer | 快照时的 current_exp |
| level | Integer | 快照时的等级 |
| coins | Integer | 快照时的硬币数 |
| recorded_at | DateTime | 记录时间 |

##### coin_records（投币记录表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | 自增 |
| account_uid | BigInteger FK | 关联 accounts.uid |
| bvid | String | 视频 BV 号 |
| aid | Integer | 视频 AV 号 |
| amount | Integer | 投币数量 |
| reason | String | 投币原因（specified/recommend/fallback） |
| created_at | DateTime | 时间 |

##### system_configs（系统配置表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | 自增 |
| key | String UNIQUE | 配置键（如 admin_username/admin_password_hash/notify_*） |
| value | Text | 配置值 |

**系统配置键列表**：
- `admin_username` / `admin_password_hash` — 管理员凭据
- `notify_on_success` / `notify_on_failure` / `notify_daily_summary` — 通知开关
- `notify_quiet_start` / `notify_quiet_end` — 免打扰时段
- `server_chan_key` — Server酱 SendKey
- `bark_key` — Bark 推送 Key
- `bark_server_url` — Bark 自建服务器 URL
- `theme` — 当前主题（22/33）
- `show_mascot` — 是否显示吉祥物

### 5.3 认证与安全

**文件**：`backend/app/deps.py`

#### 管理员认证流程
1. 登录：`POST /api/v1/auth/login` → 校验密码 → 签发 JWT → 存 localStorage `dailykyi_token`
2. 请求：前端 Axios 拦截器自动加 `Authorization: Bearer <token>`
3. 验证：`get_current_user()` 解析 JWT → 校验有效期 → 返回用户信息
4. 登出：`POST /api/v1/auth/logout` → 前端清 localStorage → `window.location.href='/login'`

#### Cookie 加密存储
```python
# 加密
def encrypt_cookie(cookie_str: str) -> str:
    key = Fernet.generate_key()  # 基于 SECRET_KEY 派生
    f = Fernet(key)
    return f.encrypt(cookie_str.encode()).decode()

# 解密
def decrypt_cookie(encrypted: str) -> str:
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()
```

#### B 站扫码登录流程
1. `POST /auth/qr` → 调 B 站 `x/passport-login/web/qrcode/generate` → 返回二维码 URL + qrcode_key
2. 前端轮询 `GET /auth/qr/status?key=xxx`（每 3 秒）→ 后端调 `x/passport-login/web/qrcode/poll`
3. 状态码映射：
   - `86101` → waiting（等待扫码）
   - `86090` → scanned（已扫码，确认中）
   - `0` → confirmed（登录成功，解析 Set-Cookie 提取 SESSDATA/bili_jct/DedeUserID）
   - `86038` → expired（二维码过期）
4. 登录成功后：加密 Cookie → 存 accounts 表 → 创建/更新 TaskConfig 默认配置

### 5.4 路由层

所有路由前缀：`/api/v1`

#### auth.py — `/api/v1/auth`
| 方法 | 路径 | 功能 |
|---|---|---|
| POST | `/login` | 管理员密码登录，返回 JWT |
| POST | `/logout` | 登出 |
| GET | `/me` | 获取当前用户信息 |
| PUT | `/change-password` | 修改管理员密码 |
| POST | `/qr` | 生成 B 站登录二维码 |
| GET | `/qr/status` | 轮询二维码扫码状态 |
| POST | `/qr/confirm` | 确认登录（存储 Cookie + 创建账号） |
| POST | `/cookie-login` | 手动 Cookie 登录（备用方式） |

#### accounts.py — `/api/v1/accounts`
| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `` | 账号列表（含 today_exp_gained，基于快照计算） |
| GET | `/{uid}` | 账号详情 |
| DELETE | `/{uid}` | 删除账号 |
| POST | `/{uid}/refresh` | 刷新账号信息（调 B 站 nav 接口） |
| POST | `/check-cookies` | 批量检测所有账号 Cookie 有效性 |

#### tasks.py — `/api/v1/tasks`
| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/{uid}` | 获取账号所有任务配置 |
| PUT | `/{uid}/{task_type}` | 更新任务配置 |
| POST | `/{uid}/{task_type}/trigger` | 手动触发任务执行 |
| POST | `/{uid}/{task_type}/preview` | 预览任务逻辑（如投币目标视频列表） |

#### logs.py — `/api/v1/logs`
| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `` | 日志列表（支持 uid/task_type/status/date/limit/offset 过滤） |
| GET | `/{log_id}` | 日志详情 |
| GET | `/stream` | SSE 实时日志流（EventSource） |

#### dashboard.py — `/api/v1/dashboard`
| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `` | 仪表盘聚合数据（账号列表+LV6预估+今日统计+最近日志+即将执行） |

#### system.py — `/api/v1/system`
| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/config` | 获取系统配置 |
| PUT | `/config` | 更新系统配置 |
| GET | `/upgrade/check` | 检查 GitHub 新版本 |
| POST | `/upgrade/execute` | 执行一键升级 |
| POST | `/notify/test` | 发送测试通知 |

#### health.py — `/api/v1/health`
| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `` | 健康检查（返回 status + version） |

### 5.5 服务层

#### bili_api.py — BiliClient

**核心 B 站 API 客户端**，所有与 B 站的交互都经过此类。

**初始化**：从 Cookie 字符串解析 `SESSDATA` / `bili_jct`（csrf）/ `DedeUserID`（uid）

**关键公开方法**：

| 方法 | 调用的 B 站接口 | 用途 |
|---|---|---|
| `get_user_info()` | `x/web-interface/nav` | 获取账号信息（等级/经验/硬币） |
| `get_daily_exp_reward()` | `x/web-interface/coin/exp` | 获取每日经验奖励状态（share/watch/login 的 bool） |
| `get_recommend_videos()` | `x/web-interface/index/top/feed/rcmd` | 获取推荐视频列表 |
| `get_videos_by_uid(uid)` | `x/space/wbi/arc/search` | 获取指定用户视频 |
| `bvid_to_aid(bvid)` | `x/web-interface/view` | BV 转 AV + 获取 cid |
| `coin_video(bvid, amount)` | `x/web-interface/coin/add` | 给视频投币 |
| `check_coin(bvid)` | `x/web-interface/coin/check` | 检查已投币状态 |
| `heartbeat(bvid, cid, played_time, ...)` | `x/click-interface/web/heartbeat` | 视频播放进度上报 |
| `share_video(bvid)` | `x/web-interface/share/add` | 分享视频 |
| `live_sign()` | `xlive/web-ucenter/v2/sign/` | 直播签到 |
| `silver2coin()` | `pay/v1/Exchange/silver2coin` | 银瓜子兑换硬币 |
| `get_coins()` | `x/web-interface/coin/getCoins` | 获取硬币余额 |
| `get_qr_code()` | `x/passport-login/web/qrcode/generate` | 生成登录二维码 |
| `get_qr_status(key)` | `x/passport-login/web/qrcode/poll` | 轮询扫码状态 |

**反风控措施**：
- 所有请求带 `User-Agent`（模拟 Chrome 浏览器）
- POST 请求自动补 `Origin: https://www.bilibili.com`
- 关键请求带 `Referer`（视频页 URL）
- 带 WBI 签名（`bili_wbi.py`）
- 带 `buvid3` 等风控指纹（`anti_detect.py`）
- 随机延迟（`random_delay` 函数）

**错误处理**：`BiliAPIException` 封装 B 站错误码和消息

#### scheduler.py — TaskScheduler

**单例调度器**，基于 APScheduler `AsyncIOScheduler`。

**核心属性**：
```python
class TaskScheduler:
    scheduler: AsyncIOScheduler
    jobs: dict[str, Any]           # job_id → APScheduler job
    _failure_counts: dict          # (uid, task_type) → 连续失败次数
    _summary_sent_cache: set       # 每日汇总已发送缓存
```

**核心方法**：
- `load_jobs(db)` — 启动时从数据库加载所有 `enabled=True` 的 TaskConfig，注册定时任务
- `register_job(db, config)` — 注册单个任务（fixed/random 模式）
- `unregister_job(uid, task_type)` — 注销任务
- `execute_task(uid, task_type)` — 执行任务（手动触发或定时触发）
- `_run_task(...)` — 内部执行逻辑：创建 TaskLog → handler.pre_check → handler.execute → 写结果
- `_try_send_daily_summary(db, uid)` — 检查该账号今日启用任务是否全部执行完，是则发汇总
- `_reset_exp_snapshot_timer()` — 任务完成后重置 6h 快照定时器
- `get_upcoming(limit)` — 获取即将执行的任务列表

**任务执行流程**：
```
execute_task(uid, task_type)
  │
  ├─ 查 Account + TaskConfig
  ├─ 创建 TaskLog(status=pending)
  │
  ├─ 根据 task_type 实例化 Handler
  │   ├─ coin     → CoinHandler
  │   ├─ watch    → WatchHandler
  │   ├─ share    → ShareHandler
  │   ├─ login    → LoginHandler
  │   ├─ live_sign → LiveSignHandler
  │   └─ silver2coin → Silver2CoinHandler
  │
  ├─ handler.pre_check()     # 调 nav 接口验证 Cookie + 刷新缓存
  │   └─ 失败 → 标记 TaskLog failed → 发失败通知
  │
  ├─ handler.execute(config) # 执行任务（含重试逻辑）
  │   └─ 返回 TaskResult(success, message, detail, exp_gained)
  │
  ├─ 写 TaskLog 结果
  │   ├─ success → status=success, 发成功通知（如果开启）
  │   ├─ 业务跳过 → status=skipped
  │   └─ 失败 → status=failed, 发失败通知（如果开启）
  │
  ├─ _reset_exp_snapshot_timer()  # 重置 6h 定时器
  └─ _try_send_daily_summary()    # 尝试发每日汇总
```

**调度模式**：
- `fixed`：定时执行，`schedule_config = {hour: 6, minute: 30}`
- `random`：在指定时段内随机执行，`schedule_config = {window_start: "06:00", window_end: "09:00"}`

**系统级定时任务**（非用户配置）：
- `cookie-checker`：每 6 小时检测所有账号 Cookie 有效性
- `exp-snapshot`：每 6 小时记录经验快照（任务执行后自动重置定时器）

### 5.6 任务处理器

**文件目录**：`backend/app/services/task_handlers/`

#### base.py — BaseTaskHandler

```python
class TaskResult(BaseModel):
    success: bool
    message: str
    detail: dict[str, Any] = {}
    exp_gained: int = 0

class BaseTaskHandler(ABC):
    task_type: str

    def __init__(self, account: Account, db: AsyncSession):
        self.account = account
        self.db = db
        self.client: BiliClient | None = None

    async def init_client(self) -> BiliClient:
        # 解密 Cookie → 创建 BiliClient

    async def pre_check(self) -> bool:
        # 调 get_user_info() 验证 Cookie + 刷新 account 缓存字段
        # 返回 False 表示 Cookie 失效

    def _apply_nav_info(self, info: dict) -> None:
        # 把 nav 返回值写入 account.level/current_exp/next_level_exp/coins

    async def refresh_exp_snapshot(self) -> int:
        # ★ v0.2.0 核心方法
        # 1. 调 get_user_info() 刷新 account.current_exp
        # 2. 查最近一条 ExpSnapshot
        # 3. 写新 ExpSnapshot
        # 4. 返回 delta = max(0, new_exp - last_exp)

    @abstractmethod
    async def execute(self, config: dict) -> TaskResult:
        # 子类实现
```

#### coin.py — CoinHandler（投币任务）

**配置参数**：
```json
{
  "mode": "fixed",              // fixed（固定数量）/ smart（按等级分级）
  "fixed_limit": 5,             // 固定模式投币数
  "smart_tiers": [              // 智能模式分级
    {"min_coins": 50, "daily_limit": 5}
  ],
  "reserve_coins": 5,           // 保留硬币数
  "target_mode": "specified",   // specified（指定 UID）/ recommend（推荐）
  "target_uids": [123456],      // 指定投币目标
  "fallback_to_recommend": true // 指定视频不足时回退推荐
}
```

**执行流程**：
1. `pre_check()` 验证 Cookie
2. `get_coins()` 获取当前硬币数
3. 计算可投币数 = min(计划数, 当前硬币 - 保留数)
4. 根据目标模式获取视频列表
5. 逐个投币（`coin_video`），跳过已投过的（`check_coin`）
6. `refresh_exp_snapshot()` 获取真实经验 delta
7. 返回 TaskResult（exp_gained = delta 或 delta/10 估算）

#### watch.py — WatchHandler（观看任务）

**配置参数**：
```json
{
  "duration_seconds": 310       // 目标观看时长（300/310/350 秒，满足 B 站 5 分钟规则）
}
```

**执行流程**：
1. `pre_check()` 验证 Cookie
2. `get_daily_exp_reward()` 检查是否已领观看经验（已领则 skip）
3. `get_recommend_videos()` 获取推荐视频
4. `bvid_to_aid(bvid)` 获取 cid
5. 发送初始 heartbeat
6. **每 15~25 秒真实等待 + 上报一次 heartbeat**，累计 `played_time` 到 target（≥300s）
7. 等待 3~5 秒让经验系统同步
8. `get_daily_exp_reward()` 复核 watch 状态
9. `refresh_exp_snapshot()` 获取真实经验 delta
10. delta ≥ 5 → 成功 +5；delta = 0 → 失败（可能别处已完成）

**关键技术点**：
- B 站要求累计观看 ≥ 5 分钟（300 秒）才给经验
- heartbeat 的 `played_time` 和 `dt` 必须匹配（dt ≈ 两次上报的时间差）
- 需带 `play_type=1` / `type=3` / `Referer` 视频页 URL

#### share.py — ShareHandler（分享任务）

**执行流程**：
1. `pre_check()` 验证 Cookie
2. `get_daily_exp_reward()` 检查是否已领分享经验
3. `get_recommend_videos()` 获取推荐视频
4. `share_video(bvid)` 调用分享接口（带 aid + share_channel=copy + spmid）
5. 等待 6~10 秒让经验系统同步
6. `get_daily_exp_reward()` 复核 share 状态
7. `refresh_exp_snapshot()` 获取真实经验 delta
8. delta ≥ 5 → 成功；delta = 0 → 失败

**已知难点**：分享接口对 IP/UA 风控较严，某些环境下可能接口返回成功但经验系统不记录。

#### login.py — LoginHandler（每日登录经验）

**执行流程**：
1. `pre_check()` 验证 Cookie（调 nav 接口本身即触发登录经验）
2. `get_daily_exp_reward()` 检查 login 状态
3. `refresh_exp_snapshot()` 获取真实经验 delta
4. delta ≥ 5 → 成功；delta = 0 → 可能别处已登录

#### live_sign.py — LiveSignHandler（直播签到）

**执行流程**：
1. `pre_check()` 验证 Cookie
2. `live_sign()` 调用直播签到接口
3. 返回 TaskResult

#### silver2coin.py — Silver2CoinHandler（银瓜子兑换）

**执行流程**：
1. `pre_check()` 验证 Cookie
2. `get_user_info()` 获取银瓜子余额
3. 余额 ≥ 70000 时调用 `silver2coin()`
4. 返回 TaskResult

### 5.7 调度器

参见 [5.5 服务层 - scheduler.py](#55-服务层) 部分。

**初始化入口**：`backend/app/main.py` 的 `lifespan` 调用 `init_scheduler()`

```python
async def init_scheduler():
    async with AsyncSessionLocal() as db:
        await scheduler.load_jobs(db)       # 加载用户任务

    # 系统级任务
    scheduler.scheduler.add_job(
        _cookie_check_job,
        trigger=IntervalTrigger(hours=6),
        id="cookie-checker",
        next_run_time=datetime.now() + timedelta(minutes=2),
    )
    scheduler.scheduler.add_job(
        _exp_snapshot_job,
        trigger=IntervalTrigger(hours=6),
        id="exp-snapshot",
        next_run_time=datetime.now() + timedelta(minutes=5),
    )
    scheduler.start()
```

### 5.8 通知服务

**文件**：`backend/app/services/notify.py`

**NotifyService** 支持两种推送渠道：
- **Server酱**：`POST https://sctapi.ftqq.com/{key}.send` → 微信公众号推送
- **Bark**：`POST https://api.day.app/{key}/{title}/{body}` → iOS 推送（支持自建服务器）

**通知类型**：
- `send_task_result(account, task_type, success, message, exp)` — 单任务结果通知
- `send_daily_summary(account, today_logs)` — 每日汇总通知
- `send_cookie_alert(account, status)` — Cookie 失效告警

**通知开关**（SystemConfig）：
- `notify_on_success` — 任务成功时推送
- `notify_on_failure` — 任务失败时推送
- `notify_daily_summary` — 每日汇总推送
- `notify_quiet_start` / `notify_quiet_end` — 免打扰时段（如 23:00-08:00）

**每日汇总触发逻辑**（v0.2.0）：
```
每个任务执行完毕后调用 _try_send_daily_summary(uid):
  1. 查该账号 enabled=True 的所有 task_type
  2. 查今日 TaskLog 中出现过的 task_type 集合
  3. 如果"已执行集合 ⊇ 启用集合" → 触发汇总
  4. 内存缓存去重（同一天同一账号只发一次）
```

### 5.9 经验快照机制（v0.2.0 核心）

**文件**：
- `backend/app/models/exp_snapshot.py` — ExpSnapshot 表
- `backend/app/services/exp_service.py` — 经验计算服务
- `backend/app/services/task_handlers/base.py` — `refresh_exp_snapshot()` 方法

#### 设计动机

旧方案用 `TaskLog.exp_gained` 之和计算"今日经验"，存在三个问题：
1. 依赖任务上报数值（曾因 bug 误报 +5）
2. 任务未执行时段不记录
3. 用户在别处设备完成任务后，Dailykyi 仍会执行并虚报

#### "主动+被动+重置"机制

```
┌──────────────────────────────────────────────────────────┐
│                    经验记录机制                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  主动记录：任务执行完毕后                                  │
│    └─ refresh_exp_snapshot()                             │
│       ├─ 调 nav 接口刷新 account.current_exp             │
│       ├─ 写一条新 ExpSnapshot                             │
│       └─ 返回与上次快照的 delta（真实经验增量）            │
│                                                          │
│  被动记录：每 6 小时自动一次                               │
│    └─ _exp_snapshot_job()                               │
│       └─ 遍历所有账号写 ExpSnapshot                       │
│                                                          │
│  重置机制：任务执行后                                     │
│    └─ _reset_exp_snapshot_timer()                        │
│       └─ 把下一次自动快照推迟到 now + 6h                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### 今日经验计算（exp_service.py）

```python
async def compute_today_exp_gain(db, acc) -> int:
    # 1. 取 24h 前 ±30 分钟窗口内的最近一条快照
    # 2. delta = max(0, current_exp - snapshot.exp)
    # 3. 无快照时 fallback 到 TaskLog.exp_gained 当日汇总
```

#### LV6 预估计算

```python
async def compute_lv6_estimate(db, acc, today_exp) -> dict:
    # LV6 阈值 = 28800 经验
    # 取最近 7 天的快照，用最早和最新的差值算日均经验
    # est_days = ceil(remaining / avg_daily_exp)
    # est_date = today + est_days
```

---

## 6. 前端详细设计

### 6.1 路由与守卫

**文件**：`frontend/src/router/index.ts`

| 路径 | 组件 | 说明 |
|---|---|---|
| `/login` | LoginView | 登录页（不需要认证） |
| `/dashboard` | DashboardView | 首页仪表盘 |
| `/tasks` | TaskConfigView | 任务配置 |
| `/accounts` | AccountManageView | 账号管理 |
| `/logs` | LogViewerView | 日志查看 |
| `/settings` | SystemSettingsView | 系统设置 |
| `/:pathMatch(.*)*` | → /dashboard | catch-all 重定向 |

**路由守卫**：
- 未登录访问受保护路由 → 重定向 `/login`
- 已登录访问 `/login` → 重定向 `/dashboard`
- 认证状态由 `auth.isLoggedIn` 控制（基于 localStorage `dailykyi_token` 存在性）

### 6.2 状态管理

**文件**：`frontend/src/stores/`

#### auth.ts
```typescript
// 状态
token: string | null       // JWT token
user: { username: string } // 当前用户
isLoggedIn: boolean        // 计算属性：token 存在且非空

// 方法
login(username, password)  // 登录 → 存 token → router.push('/dashboard')
logout()                   // 清 localStorage → 跳 /login
init()                     // 应用启动时调用，验证 token 有效性
changePassword(old, new)   // 修改密码
```

#### theme.ts
```typescript
// 状态
current: '22' | '33'      // 当前主题

// 方法
setTheme(theme)            // 切换主题 → 存 localStorage → 更新 document.dataset.theme
is22 / is33                // 计算属性
```

### 6.3 API 封装层

**文件**：`frontend/src/api/`

#### request.ts — Axios 实例
```typescript
// 基础 URL: /api/v1
// 请求拦截器：自动加 Authorization: Bearer <token>
// 响应拦截器：
//   - 200 → 返回 data
//   - 401 → 清 token → 跳 /login
//   - 其他 → ElMessage.error(message) → 抛出
```

#### 各 API 文件
| 文件 | 封装的接口 |
|---|---|
| `auth.ts` | login, logout, getMe, changePassword, getQrCode, getQrStatus, cookieLogin |
| `account.ts` | getAccounts, getAccount, deleteAccount, refreshCookie, checkCookies |
| `task.ts` | getTaskConfigs, updateTaskConfig, triggerTask, previewTask |
| `log.ts` | getLogs, getLogById, getLogStream（SSE EventSource） |
| `dashboard.ts` | getDashboard |
| `system.ts` | getSystemConfig, updateSystemConfig, checkUpgrade, runUpgrade |

### 6.4 页面视图

#### LoginView.vue
- 管理员密码登录表单
- 登录失败显示剩余尝试次数和锁定状态
- 底部版本号
- **不含**"每日姬"或"22 & 33's Daily"文字

#### DashboardView.vue
- 三列统计卡片：账号数 / 今日经验 / 任务进度
- 账号概览列表（头像、用户名、等级、经验进度、硬币、今日经验）
- **LV6 预估卡片**（v0.2.0）：显示还需经验、日均经验、预估天数和达成日期
- 今日任务统计（总任务/成功/失败/跳过）
- 最近执行日志

#### TaskConfigView.vue
- `el-tabs` 五个标签页：投币 / 观看 / 分享 / 直播签到 / 银瓜子换币
- 每个标签页内容：
  - **投币**：enabled 开关、fixed/smart 模式选择、fixed 用 el-slider(1-5)、smart 用动态分级表单、target 选择(specified/recommend)、UID 标签列表、fallback_to_recommend 复选框、实时硬币状态显示
  - **观看**：enabled 开关、duration_seconds 选择(300/310/350 秒)
  - **分享**：enabled 开关
  - **直播签到**：enabled 开关
  - **银瓜子换币**：enabled 开关
- 调度选项：fixed/random 单选 + time-picker 输入
- 每个标签页有"保存"按钮（PUT `/tasks/{uid}/{task_type}`）
- "立即测试"按钮触发任务执行

#### AccountManageView.vue
- 账号卡片列表（头像、用户名、UID、等级、经验进度条、硬币数）
- Cookie 状态标签（正常/已失效/未绑定/待检测）
- 操作按钮：配置任务（跳转 /tasks）、刷新 Cookie、删除（el-popconfirm）
- "添加账号"按钮 → 打开 KyiQrModal
- "检测 Cookie"批量按钮
- 空状态显示"还没有账号"

#### LogViewerView.vue
- 筛选栏：账号、任务类型、状态、日期
- 实时模式开关（el-switch）→ 开启时用 EventSource 连接 `/logs/stream`
- 日志时间轴（KyiTimeline 组件）：显示时间、账号、任务、状态、消息、经验
- 分页（el-pagination，limit/offset 参数）

#### SystemSettingsView.vue
- 四个设置卡片：
  1. **通知设置**：Bark key、Server酱 key、通知时机单选
  2. **风控设置**：请求间隔 min/max、最大重试次数、连续失败暂停
  3. **外观设置**：22/33 主题单选、显示吉祥物开关
  4. **安全设置**：修改密码
- **版本与升级卡片**（v0.2.0 美化）：
  - 2233 双色渐变横幅 + 用户提供的 1.png 图片
  - 当前版本号
  - "检查更新"按钮 → 调 GitHub Releases API
  - 有新版本时显示更新内容 + "一键升级"按钮
  - "已是最新版本"提示

### 6.5 组件库

| 组件 | 功能 |
|---|---|
| **KyiCard** | 通用卡片容器（标题 + 图标 + 内容区） |
| **KyiHeader** | 顶部导航栏：logo + 页面标题 + 版本检测徽章 + 用户菜单 |
| **KyiSidebar** | 侧边栏：导航菜单 + 吉祥物轮播图（mascot-22 / mascot-33 span） |
| **KyiQrModal** | B 站扫码登录弹窗：二维码展示 + 状态轮询 + Cookie 手动输入 |
| **KyiThemeSwitch** | 22/33 主题切换按钮 |
| **KyiTimeline** | 日志时间轴：formatDate 渲染时间 + 状态色标 |

### 6.6 主题系统

**文件**：`frontend/src/assets/styles/`

- `variables.css` — CSS 变量定义（`--kyi-primary`、`--kyi-secondary`、`--kyi-text` 等）
- `theme-22.css` — 22 粉色主题（`[data-theme="22"]`）
- `theme-33.css` — 33 蓝色主题（`[data-theme="33"]`）

**切换机制**：`document.documentElement.dataset.theme = '22' | '33'`

**设计约束**（用户偏好）：
- 仅使用黑白配色方案 + 主题色点缀
- 不使用 Material 风格组件（如 AppBar、Card）
- 所有 API 错误以简单文本提示，绝不显示红屏

---

## 7. 关键业务流程

### 7.1 新用户部署流程

```
git clone → cp .env.example .env → 修改 SECRET_KEY → docker compose up -d
  │
  ├─ backend 容器启动
  │   ├─ init_db() 创建所有表
  │   ├─ 首次启动：创建默认管理员（2233 / tv23333）
  │   └─ init_scheduler() 启动调度器
  │
  └─ nginx 容器启动
      └─ 提供前端静态资源 + /api 反代
```

### 7.2 账号绑定流程

```
用户登录管理面板 → 账号管理 → 添加账号
  │
  ├─ 弹出 KyiQrModal → 调 /auth/qr 获取二维码
  ├─ 前端每 3 秒轮询 /auth/qr/status
  ├─ 用户 B 站 APP 扫码 → 确认登录
  ├─ 后端获取 Cookie → 加密存储到 accounts 表
  ├─ 调 nav 接口获取账号信息（用户名/等级/经验）
  └─ 创建默认 TaskConfig（5 种任务各一条，默认 enabled=False）
```

### 7.3 每日任务执行流程

```
APScheduler 定时触发 → execute_task(uid, task_type)
  │
  ├─ 创建 TaskLog(status=pending)
  ├─ 实例化 Handler → pre_check() 验证 Cookie
  │   └─ Cookie 失效 → 标记 failed → 发 Cookie 告警通知
  │
  ├─ handler.execute(config)
  │   ├─ 执行 B 站 API 调用
  │   ├─ refresh_exp_snapshot() 获取真实经验 delta
  │   └─ 返回 TaskResult
  │
  ├─ 写 TaskLog 结果（status / message / detail / exp_gained）
  ├─ 发任务结果通知（如果开启）
  ├─ _reset_exp_snapshot_timer() 重置 6h 定时器
  └─ _try_send_daily_summary() 检查是否全部任务完成 → 发汇总
```

### 7.4 经验追踪流程

```
┌─────────────── 每 6 小时（被动）───────────────┐
│ _exp_snapshot_job()                            │
│   └─ 遍历所有账号 → 写 ExpSnapshot              │
└────────────────────┬───────────────────────────┘
                     │
┌──────────── 任务执行后（主动）──────────────────┐
│ handler.refresh_exp_snapshot()                  │
│   ├─ 调 nav 接口刷新 account.current_exp        │
│   ├─ 写新 ExpSnapshot                           │
│   ├─ 返回 delta = new_exp - last_exp            │
│   └─ _reset_exp_snapshot_timer() 推迟下次被动   │
└────────────────────┬───────────────────────────┘
                     │
┌──────────── 前端展示 ─────────────────────────┐
│ Dashboard 请求                                   │
│   ├─ compute_today_exp_gain()                   │
│   │   └─ current_exp - 24h前快照.exp = 今日增量 │
│   └─ compute_lv6_estimate()                     │
│       └─ (28800 - current_exp) / 日均经验 = 天数│
└─────────────────────────────────────────────────┘
```

---

## 8. 部署与运维

### 8.1 Docker Compose 编排

#### 生产环境（docker-compose.yml）

```yaml
services:
  backend:
    build: ./backend
    container_name: dailykyi-backend
    volumes:
      - ./data:/app/data          # SQLite 持久化
      - ./logs:/app/logs          # 日志持久化
    env_file: .env
    environment:
      - TZ=Asia/Shanghai
    ports:
      - "8000:8000"               # 内部 API（可关闭）
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  nginx:
    build: ./docker
    container_name: dailykyi-nginx
    ports:
      - "23333:80"                # 对外统一端口
    volumes:
      - ./frontend/dist:/usr/share/nginx/html  # 前端静态资源
    depends_on:
      - backend

networks:
  default:
    name: dailykyi-net
```

#### 开发环境（docker-compose.dev.yml）

```yaml
services:
  backend-dev:
    build: ./backend
    container_name: dailykyi-backend-dev
    volumes:
      - ./backend:/app            # 热重载
      - ./data:/app/data
      - ./logs:/app/logs
    env_file: .env
    environment:
      - DAILYKYI_DEBUG=True
      - DAILYKYI_LOG_LEVEL=DEBUG
      - TZ=Asia/Hong_Kong         # ★ 必须设置，否则日志时间晚 8 小时
    ports:
      - "8000:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend-dev:
    image: node:18-alpine
    container_name: dailykyi-frontend-dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "23333:3000"              # Vite 3000 → 映射 23333
    command: sh -c "cd /app && npm install && npm run dev -- --host 0.0.0.0"
```

### 8.2 Nginx 配置要点

**文件**：`docker/nginx.conf`

```nginx
server {
    listen 80;

    # 前端静态资源
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;   # Vue history 模式
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://backend:8000;     # ★ 无尾部斜杠，保留完整路径
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;

        # WebSocket 支持（如果用 WS）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    client_max_body_size 10m;
}
```

**关键约束**：`proxy_pass` **不能有尾部斜杠**，否则路径会被截断。

### 8.3 部署脚本

#### install.sh（一键部署）
```bash
# 1. 检查 git/docker/docker compose
# 2. cp .env.example .env
# 3. cd frontend && npm install && npm run build && cd ..
# 4. docker compose up -d --build
# 5. 输出访问地址和默认账号
```

#### update.sh（一键升级）
```bash
# 1. git pull --ff-only origin main
# 2. cd frontend && npm install && npm run build && cd ..
# 3. docker compose build backend
# 4. docker compose up -d
# 5. 提示数据库字段自动补充
```

### 8.4 常用运维命令

```bash
# 开发环境
docker compose -f docker-compose.dev.yml up -d          # 启动
docker compose -f docker-compose.dev.yml restart backend-dev  # 重启后端
docker compose -f docker-compose.dev.yml logs -f backend-dev  # 查看日志

# 生产环境
docker compose up -d --build                            # 构建并启动
docker compose logs -f backend                          # 查看日志
docker compose down                                     # 停止所有服务

# 数据库操作（开发环境）
docker exec dailykyi-backend-dev python -c "
  import sqlite3
  c = sqlite3.connect('/app/data/dailykyi.db')
  rows = c.execute('SELECT * FROM accounts').fetchall()
  for r in rows: print(r)
"

# 手动初始化数据库
docker exec dailykyi-backend-dev python scripts/init_db.py
```

---

## 9. 环境变量说明

**文件**：`.env.example`

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DAILYKYI_SECRET_KEY` | `change-me-please` | JWT 签名 + Cookie 加密密钥派生，**生产必须修改** |
| `DAILYKYI_LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `DAILYKYI_DATABASE_URL` | `sqlite+aiosqlite:///data/dailykyi.db` | 数据库连接串 |
| `DAILYKYI_DEFAULT_USERNAME` | `2233` | 首次启动创建的管理员用户名 |
| `DAILYKYI_DEFAULT_PASSWORD` | `tv23333` | 首次启动的管理员密码（登录后强制修改） |
| `DAILYKYI_MAX_LOGIN_ATTEMPTS` | `5` | 最大登录尝试次数 |
| `DAILYKYI_LOGIN_LOCKOUT_MINUTES` | `10` | 登录锁定时长（分钟） |

**容器环境变量**（不在 .env 中，在 docker-compose 中设置）：
- `TZ` — 时区（**dev 必须设 `Asia/Hong_Kong` 或 `Asia/Shanghai`**，否则日志时间不对）

---

## 10. 历史决策与注意事项

### 10.1 架构决策

1. **SQLite 而非 PostgreSQL/MySQL**：降低部署门槛，单文件持久化，适合个人工具。`docker compose up -d` 即可启动，无需额外数据库服务。

2. **`Base.metadata.create_all` 而非 Alembic 迁移**：项目规模较小，直接建表更简单。`init_db()` 中有兼容迁移逻辑（检查已有表缺字段时 `ALTER TABLE` 补充）。Alembic 配置保留但未实际使用。

3. **Cookie 加密存储**：使用 Fernet 对称加密，密钥从 `SECRET_KEY` 派生。即使数据库泄露，Cookie 也不会直接暴露。

4. **前后端统一端口 23333**：开发模式 Vite 3000 映射到 23333，生产模式 Nginx 80 映射到 23333。用户无论哪种模式都访问 23333。

5. **经验快照机制（v0.2.0）**：废弃 `TaskLog.exp_gained` 作为今日经验的计算来源，改用 `ExpSnapshot` 快照对比。原因：任务曾虚报 +5，且无法感知用户在别处设备获得的经验。

### 10.2 必须遵守的约束

| 约束 | 原因 |
|---|---|
| nginx `proxy_pass` 不能有尾部斜杠 | 会截断请求路径，导致 404 |
| dev 容器必须设 `TZ=Asia/Hong_Kong` | 否则容器内 UTC 时间，日志显示晚 8 小时 |
| 前端 `formatDate` 对 naive ISO 字符串走字面量解析 | Chrome 把无时区 ISO 字符串当 UTC 解析，导致偏移 8 小时 |
| `auth.ts` 不能有 `require_password_change` 相关逻辑 | 首次改密在前端 LoginView 内联处理，不走 store |
| `App.vue` 必须根据 `auth.isLoggedIn` 条件渲染 | 登录页与主布局互斥 |
| 登出必须 `window.location.href='/login'` | 确保完全重置状态，不用 router.push |
| `auth.init()` 必须在 `app.mount()` 前 await | 确保路由守卫有正确的认证状态 |
| `models/__init__.py` 必须导入所有模型 | `Base.metadata.create_all` 需要所有模型被注册 |
| 侧边栏菜单路由必须映射到指定组件 | /tasks→TaskConfigView, /accounts→AccountManageView 等 |
| LoginView 不能含"每日姬"或"22 & 33's Daily"文字 | 用户明确要求 |
| KyiSidebar 必须包含 mascot-22 和 mascot-33 span | 主题样式依赖这两个 class |
| QR 状态轮询间隔 3 秒 | 平衡实时性和服务器压力 |
| 日志实时模式用 EventSource 连接 `/api/v1/logs/stream` | SSE 而非 WebSocket |
| 投币保存用 PUT `/api/v1/tasks/{uid}/coin` | RESTful 规范 |
| `share_video` 必须带 `aid` + `share_channel` + `source` | B 站分享接口触发经验的必要参数 |

### 10.3 已踩过的坑

1. **B 站观看经验需要 ≥ 5 分钟**：早期观看时长选项是 30/60/120 秒，根本拿不到经验。v0.2.0 改为 300/310/350 秒。

2. **分享接口风控严**：即使接口返回 `code=0`，经验系统也可能不记录。需要用经验快照 delta 验证真实获得。

3. **B 站 `get_daily_exp_reward` 接口字段**：该接口只返回 `share`/`watch`/`login` 三个 bool，**不返回** `share_exp`/`login_exp`/`watch_exp` 数值字段。曾因读取不存在字段导致"假 +5"误报。

4. **SQLite `func.now()` 返回 UTC**：`server_default=func.now()` 在 SQLite 中返回 UTC 时间。解决方案：Python 层 `default=datetime.now()` 覆盖。

5. **前端 `new Date(isoString)` 时区 bug**：后端返回的 `created_at` 是 naive ISO 字符串（无时区后缀），Chrome 按 UTC 解析导致显示晚 8 小时。解决方案：`date.ts` 对 naive 字符串走字面量解析。

6. **Docker `restart` 不重读 environment**：修改 `docker-compose.dev.yml` 的 environment 后，`restart` 不会生效，必须 `up -d` 重新创建容器。

7. **每日汇总通知之前根本没接上**：v0.1.x 版本 `send_daily_summary` 方法存在但从未被调用。v0.2.0 在 `_run_task` 末尾加 `_try_send_daily_summary` 修复。

---

## 11. 已知问题与未来规划

### 11.1 当前已知问题

1. **分享任务可能仍不稳定**：B 站对分享接口的风控较严，某些 IP/UA 组合下可能接口成功但经验不记录。v0.2.0 用经验快照 delta 可以准确检测这种情况并报失败，但无法从根本上解决。终极方案可能需要用 APP 端接口（需要 access_key，扫码登录拿不到）。

2. **LV6 预估首日无数据**：需要积累至少 2 条经验快照（≥6 小时间隔）才能计算日均经验。首次部署后 6 小时内 LV6 卡片会显示"数据不足"。

3. **旧日志时间不可补救**：v0.2.0 之前写入的日志时间仍是 UTC（晚 8 小时），无法批量修正。新日志时间正确。

4. **ExpSnapshot 表无清理机制**：快照表会持续增长。建议未来加一个定时清理任务，只保留最近 30 天的快照。

### 11.2 用户偏好（必须遵守）

- **沟通语言**：中文
- **代码风格**：最小改动优先，不做全量重写
- **UI 设计**：黑白配色方案，不用 Material 风格组件
- **错误处理**：所有 API 错误以简单文本提示或静默失败，绝不显示红屏
- **自动重启**：改完代码后自动重启对应服务（.py → restart backend-dev，.vue/.ts → 不重启）

### 11.3 版本历史

| 版本 | 主要内容 |
|---|---|
| v0.1.1 | 初始发布：投币/观看/分享/直播签到/银瓜子兑换、多账号管理、实时日志、Server酱/Bark 推送、Docker 一键部署 |
| v0.2.0 | 经验快照机制（主动+被动+重置）、LV6 预估、日志本地时区修复、每日汇总按需触发、版本检测徽章、2233 UI 美化、观看时长修正为 300s+ |

### 11.4 未来可能的方向

- 快照表自动清理（保留 30 天）
- 分享任务改用 APP 端接口（需 access_key 登录方式）
- 多用户支持（目前单管理员）
- 任务执行历史统计图表
- 自定义任务脚本支持

---

## 附录：快速上手检查清单

新 AI 接手时，按以下步骤快速了解当前状态：

- [ ] 读 `.env` 确认 SECRET_KEY 和管理员配置
- [ ] `docker compose -f docker-compose.dev.yml ps` 确认容器状态
- [ ] `docker logs dailykyi-backend-dev --tail 50` 查看后端日志
- [ ] 访问 `http://localhost:23333` 确认前端可访问
- [ ] 访问 `http://localhost:8000/docs` 查看 API 文档
- [ ] 读 `backend/app/config.py` 了解所有配置项
- [ ] 读 `backend/app/models/__init__.py` 确认所有模型已注册
- [ ] 读 `backend/app/services/scheduler.py` 了解调度逻辑
- [ ] 读 `backend/app/services/task_handlers/base.py` 了解任务基类和 `refresh_exp_snapshot`
- [ ] 读 `frontend/src/router/index.ts` 了解路由表
- [ ] 读 `frontend/src/api/request.ts` 了解 Axios 拦截器
- [ ] 读 `frontend/src/utils/date.ts` 了解日期格式化的时区处理

---

*本文档由 AI 自动生成，基于 v0.2.0 代码库。如发现与实际代码不符，以代码为准。*
