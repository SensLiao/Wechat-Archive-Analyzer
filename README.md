# wxtools — 微信聊天记录解密与查询工具

> **当前版本：v0.5.0**

本地解密微信 PC 版（4.x / 3.x）的 SQLCipher 加密数据库，支持关键词搜索、全文检索、按联系人/时间筛选，导出 JSON / CSV / HTML（聊天气泡），附件自动解析与导出。支持公众号消息和朋友圈查询导出。所有数据留在本地。

**用自然语言和 AI 对话，即可完成所有操作** — 内置 `/wechat` skill，支持 Claude Code 和 Codex，无需记忆任何命令。

## 跨平台支持（v0.4.0+）

| 能力 | Windows | macOS | Linux（Wine） |
|------|---------|-------|---------------|
| 密钥提取（`key extract`） | 支持 | 支持 | — |
| 密钥导入（`key set`） | 支持 | 支持 | 支持 |
| 查询 / 导出 | 支持 | 支持 | 支持 |
| 数据目录自动发现 | 支持 | 支持 | 支持（Wine） |
| 密钥保护方式 | DPAPI | Keychain | Secret Service |
| 备用保护方式 | 密码 | 密码 | 密码 |

- **Windows**：完整支持，`key extract` 通过 kernel32 API 读取微信进程内存提取密钥
- **macOS**：完整支持，`key extract` 通过 Mach VM API 读取微信进程内存提取密钥（需 sudo）
- **Linux**：无官方微信客户端，支持 Wine 环境下的数据目录发现，通过 `key set` 导入密钥后可查询/导出

## 安装

```bash
git clone https://github.com/SensLiao/Wechat-Archive-Analyzer.git
cd Wechat-Archive-Analyzer
pip install -e .
pip install pycryptodome   # AES 解密依赖
```

要求：Python 3.9+。密钥提取支持 Windows 和 macOS；密钥导入、查询和导出全平台支持。

如果你在中文 Windows / Anaconda 环境里运行，并且项目路径包含非 ASCII 字符，建议后续统一使用 `python -X utf8 -m wxtools ...`，避免 Python 以 GBK 模式启动时读取 `.pth` 失败。

## 快速开始

> **提示：** 如果你使用 Claude Code 或 Codex，安装 skill 后直接说 `/wechat 帮我提取密钥` 即可，agent 会引导你完成以下所有步骤。

### 1. 获取密钥（一次性）

**Windows / macOS（自动提取）：**
```bash
wxtools key extract   # Windows 需管理员权限，macOS 需 sudo；微信需运行中
```
扫描微信进程内存，找到数据库的加密密钥并加密存储到 `~/.wxtools/keys/`。首次会询问是否设置密码保护，不设置则使用系统密钥��储（Windows DPAPI / macOS Keychain）。密钥永久有效，只需提取一次，后续操作不需要管理员/sudo 权限。

**Linux（手动导入）：**
```bash
wxtools key set <64字符hex密钥或json文件>
```
Linux 无官方微信客户端，通过 `key set` 导入已知密钥。密��保护使用 Secret Service 或密码。

### 2. 查询

```bash
wxtools query "关键词"
wxtools query --contact "张三" --since 2026-01-01
wxtools query --conversation "工作群" --type image --limit 50
wxtools query --surface public                         # 查询公众号消息
wxtools query --surface moments --contact "张三"       # 查询张三的朋友圈
wxtools query --surface all "关键词"                   # 跨所有数据面搜索
```

首次查询自动解密数据库并缓存。后续查询时自动检测微信数据库是否有更新，有新消息则增量解密，无更新直接用缓存。

### 3. 导出

```bash
wxtools export --contact "张三" -o ./output/
wxtools export --conversation "工作群" --since 2026-01-01
wxtools export --format html --contact "张三" -o ./output/   # HTML 聊天气泡
wxtools export --format csv --conversation "工作群" -o ./output/  # CSV 表格
wxtools export --attachments copy -o ./output/   # 同时导出附件文件
```

支持 JSON（默认）、CSV、HTML 三种格式。超过 1000 条时需确认，或加 `--yes` 跳过。`--attachments` 支持 `path`（解析路径）、`check`（检查存在）、`copy`（复制到导出目录）。

## 命令速览

| 命令 | 用途 |
|------|------|
| `wxtools key extract` | 提取密钥（一次性） |
| `wxtools key status` | 查看密钥状态 |
| `wxtools key verify` | 验证密钥有效性 |
| `wxtools key set <hex/file>` | 手动设置密钥 |
| `wxtools key set-password` | 设置密码保护 |
| `wxtools key remove-password` | 移除密码，恢复系统密钥存储 |
| `wxtools key unlock` | 临时解锁会话（缓存密钥） |
| `wxtools key lock [--all]` | 锁定会话 |
| `wxtools query "关键词"` | 搜索消息 |
| `wxtools export` | 导出聊天记录（JSON/CSV/HTML） |
| `wxtools cache status` | 查看缓存状态 |
| `wxtools cache clear` | 清除缓存 |
| `wxtools cache build-index` | 构建全文搜索索引 |
| `wxtools cache drop-index` | 删除全文搜索索引 |
| `wxtools config show` | 查看配置 |
| `wxtools config set <key> <value>` | 修改配置 |
| `wxtools app start` | 启动本地 Web App（API + 前端） |

所有命令支持 `--json` 输出结构化 JSON，`-v` / `-vv` 开启调试日志，`--password` 免交互密码。

## 通过 AI 对话使用（推荐）

安装 skill 后，你可以直接用自然语言和 AI agent 对话，agent 会自动调用 CLI 完成操作 — **无需记忆任何命令**。

### 安装 Skill

```bash
# Claude Code
python -X utf8 -m wxtools install-skill          # 安装到 ~/.claude/skills/

# Codex
python -X utf8 -m wxtools install-skill --codex  # 安装到 ~/.codex/skills/
```

### 对话示例

在 Claude Code 或 Codex 中直接说：

```
/wechat 帮我提取微信密钥
/wechat 找一下上周张三发的关于项目的消息
/wechat 导出和李四最近一个月的聊天记录，要 HTML 格式
/wechat 搜索工作群里关于"周报"的消息
/wechat 查一下我的公众号消息里有没有提到 AI 的
/wechat 导出张三的朋友圈
/wechat 密钥状态
/wechat 缓存占了多少空间
```

Agent 会自动：
- 检测环境（wxtools 是否安装、密钥是否就绪）
- 将自然语言转换为精确的 CLI 命令执行
- 处理密码解锁、增量缓存、格式选择等细节
- 遇到错误时给出修复建议并自动重试
- 大量导出前征求确认

> **隐私说明：** 所有数据解密和查询在本地完成，CLI 不联网。AI agent 可能使用云端推理处理你的自然语言请求，但原始聊天记录不会上传。

## 缓存机制

- 解密后的 SQLite 缓存在 `~/.wxtools/cache/<wxid>/`
- 每次查询/导出前自动比较源数据库和缓存的修改时间
- 微信收到新消息 → 源 DB 文件 mtime 更新 → 下次查询自动重新解密该文件
- 手动清除：`wxtools cache clear`

## 安全

- 所有数据（密钥、缓存、配置）存储在 `~/.wxtools/`，不上传
- 密钥用系统密钥存储（DPAPI / Keychain / Secret Service）或用户密码（Fernet + scrypt）加密存储
- 只读取微信数据库副本，不修改原始文件
- 管理员权限仅用于密钥提取（读取进程内存）

## 常见问题

**管理员权限是必须的吗？** 只有 `key extract` 需要（读取微信进程内存）。提取一次后，查询和导出不需要。

**密钥需要重复提取吗？** 不需要。密钥永久有效，除非微信大版本更新改变加密方式。

**新消息怎么同步？** 自动。每次查询时检测源数据库修改时间，有更新则重新解密对应文件。

**找不到数据库？** 手动指定路径：
```bash
wxtools config set wechat_data_dir "C:\Users\你的用户名\Documents\xwechat_files"
```

**多账号？**
```bash
wxtools key status                          # 查看所有账号
wxtools query "关键词" --account wxid_xxx   # 指定账号查询
wxtools config set active_account wxid_xxx  # 设置默认账号
```

## 版本历史

### v0.5.0 — 本地信息工作台（当前版本）

v5 新增完整的 GUI 界面，将 CLI 工具升级为可视化本地信息工作台。

| 功能 | 说明 |
|------|------|
| 应用服务层 | 业务逻辑从 CLI 解耦为 7 个独立 service，CLI / API / Skill 共享 |
| FastAPI Web API | 19 个 REST 端点，`127.0.0.1` 本地绑定，启动时生成一次性 session token |
| React 前端 | 5 个页面（首页 / 搜索 / 工作区 / 导出 / 设置），三栏布局，暖色调档案桌视觉 |
| 搜索中心 | 分面过滤（联系人、群聊、日期、类型）+ 结果流 + 上下文抽屉 |
| 工作区 | 跨数据面收集材料，JSON 文件持久化，支持标签和笔记 |
| 导出向导 | 4 步引导：数据源 → 模板 → 格式 → 执行 |
| GUI 启动 | `wxtools app start` 一键启动后端 + 前端，自动打开浏览器 |
| Electron PoC | 桌面壳概念验证，Python sidecar + 健康轮询 + 自动关闭 |
| Python 3.9+ | 最低版本降至 3.9（`from __future__ import annotations` 兼容） |

### v0.4.1 — E2E 验证与修复

- 修复 `key verify` 在 Windows 上始终返回 0/N 的问题（路径分隔符不匹配 + HMAC 输入范围错误）
- 修复 `cache build-index` 索引 0 条消息的问题（4.x 列名 `real_sender_id` 适配 + blob 内容跳过）
- 修复 Windows GBK 终端输出 emoji/CJK 崩溃（强制 UTF-8 输出）
- `key extract` 跳过 `favorite.db`（密钥存于服务器端，本地内存不存在）
- FTS 索引现在包含公众号消息（`biz_message_*.db`）

### v0.4.0 — 跨平台

- 密钥保护抽象层：统一 DPAPI、macOS Keychain、Linux Secret Service、密码文件四种后端
- `key set` 成为跨平台标准密钥导入入口
- `key extract` 新增 macOS 支持（Mach VM API 内存扫描）
- macOS / Linux 数据目录自动发现适配器
- CI 扩展至 Windows、macOS、Ubuntu 三平台矩阵

### v0.3.0

v3 新增功能：

| 功能 | 说明 |
|------|------|
| 数据面切换 | `--surface` 参数支持 chat/public/moments/all 四种数据面 |
| 公众号消息 | `--surface public` 查询/导出公众号消息（biz_message DB） |
| 朋友圈 | `--surface moments` 查询/导出朋友圈动态、评论、点赞 |
| CI 流水线 | GitHub Actions CI：pytest + ruff + compileall + secret scan |
| 安全清理 | 工作区 secret scan，git history 审计，lint 问题全部修复 |

### v0.2.0

v2 新增功能：

| 功能 | 说明 |
|------|------|
| 密钥验证 | `key verify` 验证存储密钥与加密数据库匹配，返回逐库通过/失败统计 |
| 手动设密钥 | `key set` 接受 64 字符 hex 或 JSON 密钥文件，验证后存储 |
| 会话解锁 | `key unlock/lock` 临时缓存解密密钥，避免重复输入密码，支持 TTL |
| 全文搜索 | `cache build-index` 构建 FTS5 索引，CJK 分词优化，中文子串秒级检索 |
| CSV 导出 | `export --format csv` 平铺表格格式，方便 Excel / 数据分析 |
| HTML 导出 | `export --format html` 微信风格聊天气泡 UI，每个会话独立页面 + 导航 |
| 附件处理 | `export --attachments [path\|check\|copy]` 解析附件路径、检查存在、复制到导出目录 |
| 分页查询 | DbReader 新增 `count_messages` / `search_page` / `iter_messages` 分页接口 |

### v0.1.0

完整的 v1 功能实现：

| 功能 | 说明 |
|------|------|
| 密钥提取 | 扫描微信进程内存，HMAC-SHA512 验证，17 个数据库逐一匹配派生密钥 |
| 密钥存储 | 系统密钥存储（DPAPI / Keychain / Secret Service）或用户密码（Fernet + scrypt），首次使用引导选择 |
| 数据库解密 | SQLCipher 4 直接 AES-256-CBC 解密，原子写入，按 mtime 增量更新 |
| 消息查询 | 关键词、联系人、群聊、时间范围、消息类型多维筛选，跨分片聚合 |
| 联系人解析 | 从 contact.db 读取昵称/备注名，Name2Id 表映射发送者 |
| 消息导出 | JSON 格式，按会话拆分文件 + manifest 索引，流式写入 |
| 缓存管理 | 自动缓存解密结果，mtime 检测增量更新，支持手动清除 |
| 配置系统 | YAML 配置文件 + 环境变量覆盖，支持多账号切换 |
| CLI 框架 | Click 框架，所有命令支持 `--json` 结构化输出和 `-v` 调试日志 |
| 原生 SQL | 调试用的直接 SQL 查询接口 |
| AI Skill | Claude Code 和 Codex 双平台 `/wechat` skill |
| 日志脱敏 | 自动过滤日志中的密钥 hex 内容 |
| 错误体系 | 统一错误码 + 修复建议，JSON 和人类可读双格式 |
| 3.x 兼容 | 向后兼容微信 3.x 的数据库路径和表结构 |

## GUI & Desktop App（v0.5.0+）

### Web UI（浏览器）

```bash
wxtools app start                     # 启动本地 Web App，自动打开浏览器
wxtools app start --port 9000         # 自定义端口
wxtools app start --no-open           # 不自动打开浏览器
```

FastAPI 后端（19 个 API 端点）+ React 前端，运行在 `127.0.0.1:8808`，所有数据本地处理。启动时生成一次性 session token，通过 URL 参数自动传入前端。

**页面：**
- **首页** — 账号概览、密钥状态、缓存统计、快捷操作
- **搜索中心** — 关键词 + 分面过滤（联系人 / 群聊 / 日期 / 类型 / 数据面），三栏布局
- **工作区** — 跨数据面收集材料、添加标签和笔记，JSON 文件持久化
- **导出向导** — 4 步引导式导出（数据源 → 模板 → 格式 → 执行）
- **设置** — 账号管理、密钥操作、缓存控制

**构建前端（开发者）：**
```bash
cd web
npm install
npm run build    # 产物输出到 web/dist/
npm run dev      # 开发模式（Vite，HMR）
```

### REST API

API 绑定 `127.0.0.1`，不暴露公网。所有受保护端点需要 `X-Session-Token` 请求头。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查（无需认证） |
| GET | `/api/accounts` | 账号列表 |
| GET | `/api/home/summary` | 首页聚合数据 |
| GET | `/api/key/status` | 密钥状态 |
| POST | `/api/key/extract` | 提取密钥 |
| POST | `/api/key/verify` | 验证密钥 |
| GET | `/api/cache/status` | 缓存状态 |
| POST | `/api/query/search` | 搜索消息 |
| POST | `/api/query/context` | 获取消息上下文 |
| GET | `/api/workspaces` | 工作区列表 |
| POST | `/api/workspaces` | 创建工作区 |
| GET/DELETE | `/api/workspaces/{id}` | 获取/删除工作区 |
| GET | `/api/export/templates` | 导出模板列表 |
| POST | `/api/export/run` | 执行导出 |
| GET | `/api/docs` | Swagger UI（交互式 API 文档） |

### Desktop App（Electron PoC）

Electron 桌面壳，将 Web App 封装为原生窗口：

```bash
cd desktop
npm install
npm start
```

自动启动 Python 后端、等待就绪、打开桌面窗口，关闭窗口时自动停止后端。

> **注意：** 这是概念验证（PoC）。生产级桌面 App 可考虑 Tauri（更小体积、更低内存）。

## License

MIT
