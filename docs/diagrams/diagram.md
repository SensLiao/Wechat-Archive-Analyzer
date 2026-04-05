  1. 整体架构图（Architecture Overview）

  Create a clean, modern architecture diagram for "wxtools" — a local-first WeChat chat history decryption toolkit. Show
   these layers from top to bottom:

  Top layer: "User Interface" with 3 entry points side by side:
    - Claude Code / Codex (/wechat skill)
    - CLI (wxtools commands)
    - Web UI (React + Electron PoC)

  Middle layer: "Application Services" — 7 service modules fanning out from a shared service layer

  Below that: "Core Engine" with 3 main modules:
    - Key Extractor (memory scan → HMAC-SHA512 validation)
    - DB Decryptor (SQLCipher 4, AES-256-CBC)
    - Query Engine (FTS5, cross-shard aggregation)

  Bottom layer: "Data" showing:
    - WeChat encrypted DBs (source, read-only)
    - ~/.wxtools/ (keys, cache, config)
    - Export outputs (JSON / CSV / HTML)

  Use a warm color palette (amber, cream, brown tones — archival desk aesthetic). Flat design, no 3D. Label all arrows
  with data flow direction. Include a lock icon on the key storage and a shield icon indicating "all data stays local".
  PNG, 1200x800, white background.

  ---
  2. 密钥提取与使用流程图（Key Extraction Flow）

  Create a step-by-step flowchart showing the wxtools key extraction and usage lifecycle:

  Phase 1 — "One-time Key Extraction" (highlighted):
    1. User runs "wxtools key extract" (with admin/sudo badge)
    2. Tool scans WeChat process memory
    3. Finds raw key material
    4. HMAC-SHA512 derives per-database keys
    5. Validates against 17 encrypted databases
    6. Encrypts and stores keys to ~/.wxtools/keys/ (show DPAPI/Keychain/password options as branches)

  Phase 2 — "Daily Usage" (no admin needed):
    7. User runs query/export command
    8. Keys auto-loaded from secure storage
    9. SQLCipher decryption → cached SQLite
    10. Query/export from cache

  Use a vertical flow layout. Color Phase 1 in amber/orange (one-time), Phase 2 in green (routine). Add a dotted line
  separating the two phases with label "Admin privileges only needed above this line". Include lock/unlock icons. Clean
  flat style, 1000x1400, light background.

  ---
  3. 缓存与增量更新机制（Cache & Incremental Sync）

  Create a diagram explaining the wxtools incremental cache mechanism:

  Left side: "WeChat App" with database files (msg_0.db, msg_1.db, contact.db...) each showing an mtime timestamp.

  Center: A decision diamond labeled "mtime changed?" with two paths:
    - YES → "Re-decrypt this DB shard" → update cache file
    - NO → "Skip, use existing cache"

  Right side: "~/.wxtools/cache/" with corresponding decrypted SQLite files, each with their cached mtime.

  Bottom: Arrow from cache to "Query Engine" and "Export Engine".

  Show this as a left-to-right flow. Use file icons for databases. Highlight the mtime comparison with a magnifying
  glass icon. Use blue for source DBs (read-only), green for cache (writable). Add a note: "No full re-decryption — only
   changed shards are updated". Clean infographic style, 1200x600.

  ---
  4. 数据面（Surface）查询模型（Data Surfaces）

  Create a conceptual diagram showing wxtools' 4 data surfaces:

  Center: A user icon with a search bar labeled "wxtools query"

  Four quadrants radiating outward, each a distinct surface:
    1. "chat" (top-left) — icon: speech bubbles — private and group messages, msg_*.db
    2. "public" (top-right) — icon: megaphone — official account articles, biz_message_*.db
    3. "moments" (bottom-left) — icon: camera/photo — friend circle posts, comments, likes, moments DB
    4. "all" (bottom-right) — icon: globe — cross-surface unified search

  Show the --surface flag connecting user to each quadrant. Each quadrant should list: surface name, data source DB
  pattern, and example query. Use distinct warm colors for each quadrant. Include a note showing the CLI syntax:
  --surface chat|public|moments|all. Modern card-style layout, 1200x800.

  ---
  5. AI Skill 交互流程（Natural Language → CLI Pipeline）

  Create a sequence diagram showing how the /wechat AI skill translates natural language to CLI execution:

  Actors (left to right): User, Claude Code Agent, /wechat Skill, wxtools CLI, Local Data

  Flow:
  1. User says: "找一下上周张三发的关于项目的消息"
  2. Agent activates /wechat skill
  3. Skill checks: wxtools installed? → yes
  4. Skill checks: key ready? → yes
  5. Skill translates to: wxtools query "项目" --contact "张三" --since 2026-03-29 --json
  6. CLI executes query against local cache
  7. Results returned as structured JSON
  8. Agent formats and presents results to user in natural language

  Show error handling branch: if key not ready → guide user through "wxtools key extract" first.

  Use a swimlane/sequence diagram style. Highlight the NL→CLI translation step with a sparkle/magic icon. Warm tones,
  clean lines, 1200x700.

  ---
  6. 安全模型（Security Model）

  Create a security architecture diagram for wxtools showing data protection layers:

  Center: "~/.wxtools/" directory as a vault/safe icon

  Three protection layers shown as concentric rings:
    Ring 1 (innermost): "Key Storage" — encrypted keys
      - Windows: DPAPI badge
      - macOS: Keychain badge
      - Linux: Secret Service badge
      - Fallback: Password (Fernet + scrypt)

    Ring 2: "Cache" — decrypted SQLite files
      - Local filesystem only
      - User-permission protected

    Ring 3: "Network boundary"
      - "127.0.0.1 only" for Web API
      - "One-time session token" for API auth
      - "No outbound connections" — crossed-out cloud icon

  Left side: "WeChat DBs" with a "READ ONLY" stamp — arrow going into the system but no arrow going back.

  Right side: "Export" outputs with format icons (JSON, CSV, HTML) — data flows out only to local filesystem.

  Use a shield/fortress metaphor. Dark background with glowing protective layers. Icons for each security mechanism.
  1200x800.

  ---
  这 6 张图覆盖了 README 中最核心且最适合可视化的概念：

  ┌─────┬───────────────┬──────────────────────────────┐
  │  #  │     图表      │        解决的理解障碍        │
  ├─────┼───────────────┼──────────────────────────────┤
  │ 1   │ 架构总览      │ 项目全貌，各层关系           │
  ├─────┼───────────────┼──────────────────────────────┤
  │ 2   │ 密钥流程      │ 最常被问的"为什么需要管理员" │
  ├─────┼───────────────┼──────────────────────────────┤
  │ 3   │ 缓存机制      │ 增量更新的自动化逻辑         │
  ├─────┼───────────────┼──────────────────────────────┤
  │ 4   │ 数据面模型    │ 4 种 surface 的区别和用法    │
  ├─────┼───────────────┼──────────────────────────────┤
  │ 5   │ AI Skill 流程 │ 自然语言到 CLI 的转换链路    │
  ├─────┼───────────────┼──────────────────────────────┤
  │ 6   │ 安全模型      │ 用户最关心的隐私保护         │
  └─────┴───────────────┴──────────────────────────────┘