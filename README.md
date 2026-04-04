# wxtools -- 微信聊天记录解密与查询工具

本地优先的微信 PC 版聊天记录解密、查询和导出工具。所有数据始终保存在本地，不上传任何内容。

## 功能特性

- 从运行中的微信进程内存中自动提取数据库加密密钥（一次性操作）
- 解密微信 4.x 的全部 SQLCipher 4 加密数据库
- 按关键词、联系人、时间范围、消息类型搜索聊天记录
- 将聊天记录导出为 JSON 文件
- 密钥使用 DPAPI 或用户密码（Fernet/scrypt）加密存储
- 解密后的数据库自动缓存，避免重复解密
- 支持 Claude Code `/wechat` 技能集成，可用自然语言查询聊天记录

## 安装

需要 Python 3.10 或更高版本。

```bash
# 克隆仓库
git clone <repo-url>
cd Wechat_tools_for_claude_code

# 安装（开发模式）
pip install -e .
```

核心依赖会自动安装：
- `cryptography` -- 密钥加密存储（Fernet/DPAPI）
- `click` -- 命令行框架
- `psutil` -- 进程查找
- `pyyaml` -- 配置文件

另需手动安装 `pycryptodome`（用于 AES-CBC 数据库解密）：

```bash
pip install pycryptodome
```

## 快速开始

### 1. 确保微信正在运行并已登录

密钥提取需要微信进程处于运行状态。

### 2. 以管理员权限打开终端

密钥提取需要读取微信进程内存，必须使用管理员权限。

### 3. 提取密钥

```bash
wxtools key extract
```

工具会自动扫描微信进程内存，找到每个数据库的加密密钥并验证。提取到的密钥默认使用 Windows DPAPI 加密后存储在 `~/.wxtools/keys/` 目录下。

### 4. 查询聊天记录

```bash
# 搜索包含"吃饭"的消息
wxtools query "吃饭"

# 搜索特定联系人的消息
wxtools query --contact "张三"

# 搜索指定时间范围
wxtools query "会议" --since 2026-01-01 --until 2026-03-31
```

首次查询时，工具会自动解密数据库并缓存到 `~/.wxtools/cache/`，后续查询直接使用缓存。

## 命令参考

### key -- 密钥管理

```bash
# 从微信进程提取密钥（需要管理员权限）
wxtools key extract
wxtools key extract --account wxid_xxxxxx

# 查看已存储的密钥状态
wxtools key status

# 为已存储的密钥设置密码保护（替代 DPAPI）
wxtools key set-password
wxtools key set-password --account wxid_xxxxxx

# 移除密码保护，恢复 DPAPI
wxtools key remove-password
wxtools key remove-password --account wxid_xxxxxx
```

### query -- 消息查询

```bash
# 关键词搜索
wxtools query "关键词"

# 按联系人筛选
wxtools query --contact "联系人名称"

# 按群聊/会话筛选
wxtools query --conversation "群名称"

# 按时间范围筛选
wxtools query --since 2026-01-01 --until 2026-03-31

# 按消息类型筛选
wxtools query --type image

# 限制返回数量和分页
wxtools query "关键词" --limit 50 --offset 100

# 原始 SQL 查询（调试用）
wxtools query --sql "SELECT * FROM message LIMIT 10"

# JSON 格式输出
wxtools --json query "关键词"

# 指定账号
wxtools query "关键词" --account wxid_xxxxxx
```

### export -- 导出

```bash
# 导出特定联系人的聊天记录
wxtools export --contact "张三"

# 导出特定群聊
wxtools export --conversation "工作群"

# 导出指定时间范围
wxtools export --since 2026-01-01 --until 2026-03-31

# 指定输出路径
wxtools export --contact "张三" -o ./output/

# 限制导出数量
wxtools export --limit 5000

# 跳过大量导出确认（超过 1000 条时需确认）
wxtools export --yes
```

导出格式目前仅支持 JSON。多个会话会输出到独立文件并生成 `manifest.json` 索引。

### cache -- 缓存管理

```bash
# 查看缓存状态（大小、数据库数量、解密时间）
wxtools cache status

# 清除所有缓存
wxtools cache clear

# 清除指定账号的缓存
wxtools cache clear --account wxid_xxxxxx

# 跳过确认
wxtools cache clear --yes
```

### config -- 配置管理

```bash
# 查看当前配置
wxtools config show

# 设置配置项
wxtools config set default_limit 200
wxtools config set wechat_data_dir "C:\Users\xxx\Documents\xwechat_files"
wxtools config set active_account wxid_xxxxxx
```

配置文件位于 `~/.wxtools/config.yaml`。

### 全局选项

```bash
# JSON 格式输出（适合程序调用）
wxtools --json <command>

# 调试模式
wxtools -v <command>    # INFO 级别日志
wxtools -vv <command>   # DEBUG 级别日志

# 查看版本
wxtools --version
```

## Claude Code 集成

wxtools 提供 `/wechat` 技能，可在 Claude Code 中用自然语言查询微信聊天记录。

### 安装技能

```bash
wxtools install-skill
```

### 使用示例

在 Claude Code 中输入：

```
/wechat 帮我找一下上周张三发给我的关于项目进度的消息
/wechat 导出和李四的所有聊天记录
/wechat 密钥状态
```

技能会自动将自然语言映射到对应的 CLI 命令执行。

### 卸载技能

```bash
wxtools uninstall-skill
```

## 技术细节

- 微信 4.x 使用 SQLCipher 4 加密数据库，算法为 AES-256-CBC + PBKDF2-SHA512 + HMAC-SHA512
- 页大小 4096 字节，PBKDF2 迭代次数 256000
- 每个数据库文件前 16 字节为盐值（salt），据此派生独立的加密密钥
- 微信数据目录下约有十余个数据库文件（contact、message 等），每个都有独立的派生密钥
- 密钥提取原理：扫描微信进程内存中的 32 字节候选值，通过 HMAC-SHA512 验证是否为有效密钥
- 提取到的密钥使用 DPAPI（Windows 系统级加密）或用户密码（Fernet + scrypt）加密存储
- 解密后的 SQLite 数据库缓存在 `~/.wxtools/cache/<wxid>/`，按源数据库修改时间判断是否需要重新解密

## 安全说明

- **纯本地运行**：所有数据（密钥、解密缓存、配置、日志）均保存在本地 `~/.wxtools/` 目录，不上传任何内容
- **密钥加密存储**：提取的密钥默认使用 Windows DPAPI 加密，仅当前 Windows 用户可解密；也可选择设置用户密码（Fernet + scrypt 加密）
- **只读操作**：工具只读取微信数据库文件的副本，不修改原始数据
- **管理员权限仅用于密钥提取**：密钥提取需要读取微信进程内存，因此需要管理员权限；后续的查询和导出操作不需要管理员权限
- **原子写入**：解密操作使用临时文件 + 原子重命名，避免写入不完整的文件

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / 11 |
| Python | 3.10+ |
| 微信版本 | 4.x（目标版本 4.1.7.59） |
| 权限 | 管理员权限（仅密钥提取时需要） |
| 磁盘空间 | 解密缓存约需与微信数据库同等大小的空间 |

微信数据默认路径：
- 4.x：`C:\Users\<用户名>\Documents\xwechat_files\wxid_<hash>\db_storage\`
- 3.x：`C:\Users\<用户名>\Documents\WeChat Files\<wxid>\Msg\`

工具优先检查 4.x 路径，找不到时回退到 3.x。

## 常见问题

### "WeChat not running" 错误

确保微信 PC 版正在运行且已登录。工具通过进程名（`WeChat.exe` 或 `Weixin.exe`）查找微信进程。

### "Admin privileges required" 错误

密钥提取需要管理员权限。右键点击终端，选择"以管理员身份运行"。

### 找不到数据库目录

如果自动检测失败，手动指定路径：

```bash
wxtools config set wechat_data_dir "C:\Users\你的用户名\Documents\xwechat_files"
```

### 解密失败

- 确认密钥是在微信运行时提取的
- 微信版本更新后可能需要重新提取密钥
- 使用 `wxtools key extract` 重新提取

### 查询没有结果

- 确认缓存已生成：`wxtools cache status`
- 微信数据库更新后需清除缓存重新解密：`wxtools cache clear`

### 多账号切换

```bash
# 查看所有已存储密钥
wxtools key status

# 指定查询某个账号
wxtools query "关键词" --account wxid_xxxxxx

# 或设置默认账号
wxtools config set active_account wxid_xxxxxx
```

## 许可证

MIT License
