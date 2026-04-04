# wxtools — 微信聊天记录解密与查询工具

> **当前版本：v0.1.0**

本地解密微信 PC 版（4.x）的 SQLCipher 加密数据库，支持关键词搜索、按联系人/时间筛选、导出 JSON。所有数据留在本地。

提供 Claude Code 和 Codex 的 `/wechat` skill，可用自然语言查询聊天记录。

## 安装

```bash
git clone https://github.com/SensLiao/Wechat-Archive-Analyzer.git
cd Wechat-Archive-Analyzer
pip install -e .
pip install pycryptodome   # AES 解密依赖
```

要求：Windows 10/11，Python 3.10+，微信 PC 4.x。

如果你在中文 Windows / Anaconda 环境里运行，并且项目路径包含非 ASCII 字符，建议后续统一使用 `python -X utf8 -m wxtools ...`，避免 Python 以 GBK 模式启动时读取 `.pth` 失败。

## 快速开始

### 1. 提取密钥（一次性，需管理员权限 + 微信运行中）

```bash
wxtools key extract
```

扫描微信进程内存，找到 17 个数据库的加密密钥并加密存储到 `~/.wxtools/keys/`。首次会询问是否设置密码保护，不设置则使用 Windows DPAPI。

**密钥永久有效**，只需提取一次。后续所有操作不需要管理员权限。

### 2. 查询

```bash
wxtools query "关键词"
wxtools query --contact "张三" --since 2026-01-01
wxtools query --conversation "工作群" --type image --limit 50
```

首次查询自动解密数据库并缓存。后续查询时自动检测微信数据库是否有更新，有新消息则增量解密，无更新直接用缓存。

### 3. 导出

```bash
wxtools export --contact "张三" -o ./output/
wxtools export --conversation "工作群" --since 2026-01-01
```

超过 1000 条时需确认，或加 `--yes` 跳过。输出 JSON 格式。

## 命令速览

| 命令 | 用途 |
|------|------|
| `wxtools key extract` | 提取密钥（一次性） |
| `wxtools key status` | 查看密钥状态 |
| `wxtools key set-password` | 设置密码保护 |
| `wxtools key remove-password` | 移除密码，恢复 DPAPI |
| `wxtools query "关键词"` | 搜索消息 |
| `wxtools export` | 导出聊天记录 |
| `wxtools cache status` | 查看缓存状态 |
| `wxtools cache clear` | 清除缓存 |
| `wxtools config show` | 查看配置 |
| `wxtools config set <key> <value>` | 修改配置 |

所有命令支持 `--json` 输出结构化 JSON，`-v` / `-vv` 开启调试日志。

## AI Skill 集成

### Claude Code

```bash
python -X utf8 -m wxtools install-skill          # 安装到 ~/.claude/skills/
python -X utf8 -m wxtools uninstall-skill        # 卸载
```

### Codex

```bash
python -X utf8 -m wxtools install-skill --codex  # 安装到 ~/.codex/skills/
python -X utf8 -m wxtools uninstall-skill --codex
```

安装后在对话中输入：

```
/wechat 找一下上周张三发的关于项目的消息
/wechat 导出和李四的聊天记录
/wechat 密钥状态
```

## 缓存机制

- 解密后的 SQLite 缓存在 `~/.wxtools/cache/<wxid>/`
- 每次查询/导出前自动比较源数据库和缓存的修改时间
- 微信收到新消息 → 源 DB 文件 mtime 更新 → 下次查询自动重新解密该文件
- 手动清除：`wxtools cache clear`

## 安全

- 所有数据（密钥、缓存、配置）存储在 `~/.wxtools/`，不上传
- 密钥用 DPAPI 或用户密码（Fernet + scrypt）加密存储
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

### v0.1.0（当前版本）

完整的 v1 功能实现：

| 功能 | 说明 |
|------|------|
| 密钥提取 | 扫描微信进程内存，HMAC-SHA512 验证，17 个数据库逐一匹配派生密钥 |
| 密钥存储 | DPAPI（Windows 默认）或用户密码（Fernet + scrypt），首次使用引导选择 |
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

## License

MIT
