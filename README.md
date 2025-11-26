# ZotWatch

ZotWatch 是一个基于 Zotero 文库构建个人研究兴趣画像，并持续监测学术信息源的智能文献推荐系统。支持 AI 摘要生成、增量嵌入计算，可在本地手动执行或通过 GitHub Actions 自动运行。

## 功能概览

- **Zotero 同步**：通过 Zotero Web API 获取文库条目，支持增量更新
- **智能画像构建**：使用 Voyage AI 向量化条目，支持增量嵌入计算（仅处理新增/变更条目）
- **多源候选抓取**：支持 Crossref、arXiv 数据源
- **智能评分排序**：结合语义相似度、时间衰减、引用指标、期刊质量及白名单加分
- **AI 摘要生成**：通过 OpenRouter API 调用 Claude 等模型，生成结构化论文摘要
- **多格式输出**：RSS 订阅、响应式 HTML 报告、推送回 Zotero

## 快速开始

### 1. 克隆仓库并安装依赖

```bash
git clone <your-repo-url>
cd ZotWatch
uv sync
```

### 2. 安装 Camoufox 浏览器

ZotWatch 使用 [Camoufox](https://github.com/nicholaswan/camoufox)（基于 Firefox 的反检测浏览器）从受 Cloudflare 保护的出版商网站抓取论文摘要。安装依赖后需要下载浏览器二进制文件：

```bash
python -m camoufox fetch
```

> **注意**：首次下载约需 1-2 分钟，浏览器文件约 200MB。GitHub Actions 会自动处理此步骤并缓存。

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的 API 密钥：

```bash
cp .env.example .env
```

必需的环境变量：
- `ZOTERO_API_KEY`：[Zotero API 密钥](https://www.zotero.org/settings/keys)
- `ZOTERO_USER_ID`：Zotero 用户 ID（在 API 密钥页面可见）
- `VOYAGE_API_KEY`：[Voyage AI API 密钥](https://dash.voyageai.com/)（用于文本嵌入）
- `OPENROUTER_API_KEY`：[OpenRouter API 密钥](https://openrouter.ai/keys)（用于 AI 摘要，可选）

可选的环境变量：
- `CROSSREF_MAILTO`：Crossref 礼貌池邮箱

### 5. 运行

```bash
# 首次全量画像构建（计算所有条目的嵌入）
uv run zotwatch profile --full

# 增量更新画像（仅计算新增/变更条目的嵌入）
uv run zotwatch profile

# 日常监测（默认生成 RSS + HTML 报告 + AI 摘要，推荐 20 篇）
uv run zotwatch watch

# 只生成 RSS
uv run zotwatch watch --rss

# 只生成 HTML 报告
uv run zotwatch watch --report

# 自定义推荐数量
uv run zotwatch watch --top 50
```

## CLI 命令

### `zotwatch profile`

构建或更新用户研究画像。

```bash
zotwatch profile [OPTIONS]

Options:
  --full    全量重建（重新计算所有嵌入）
```

默认使用增量模式，仅对新增或内容变更的条目计算嵌入向量，大幅减少 API 调用。

### `zotwatch watch`

获取、评分并输出论文推荐。

```bash
zotwatch watch [OPTIONS]

Options:
  --rss        只生成 RSS 订阅源
  --report     只生成 HTML 报告
  --top N      保留前 N 条结果（默认 20）
  --push       推送推荐到 Zotero
```

默认行为：
- 同时生成 RSS 和 HTML 报告
- 自动为所有推荐论文生成 AI 摘要
- 推荐数量默认 20 篇

## 目录结构

```
ZotWatch/
├── src/zotwatch/           # 主包
│   ├── core/               # 核心模型和协议
│   ├── config/             # 配置管理
│   ├── infrastructure/     # 存储、嵌入、HTTP 客户端
│   │   ├── storage/        # SQLite 存储
│   │   └── embedding/      # Voyage AI + FAISS
│   ├── sources/            # 数据源（arXiv、Crossref 等）
│   ├── llm/                # LLM 集成（OpenRouter）
│   ├── pipeline/           # 处理管道
│   ├── output/             # 输出生成（RSS、HTML）
│   └── cli/                # Click CLI
├── config/
│   └── config.yaml         # 统一配置文件
├── data/                   # 画像/缓存（不纳入版本控制）
├── reports/                # 生成的 RSS/HTML 输出
└── .github/workflows/      # GitHub Actions 配置
```

## 配置说明

所有配置集中在 `config/config.yaml`：

```yaml
# Zotero API 设置
zotero:
  api:
    user_id: "${ZOTERO_USER_ID}"
    api_key: "${ZOTERO_API_KEY}"

# 数据源开关
sources:
  arxiv:
    enabled: true
    categories: ["cs.LG", "cs.CV", "cs.AI"]
  crossref:
    enabled: true
  # ...

# 评分权重
scoring:
  weights:
    similarity: 0.50
    recency: 0.15
    # ...

# 嵌入模型
embedding:
  provider: "voyage"
  model: "voyage-3.5"

# LLM 摘要
llm:
  enabled: true
  provider: "openrouter"
  model: "anthropic/claude-3.5-sonnet"
```

## GitHub Actions 自动运行

通过 GitHub Actions 实现每日自动监测和推送，无需本地运行。

### 1. Fork 仓库

点击 GitHub 页面右上角的 **Fork** 按钮。

### 2. 配置 Secrets

在你的仓库中进入 **Settings → Secrets and variables → Actions → New repository secret**，添加以下密钥：

| Secret 名称 | 必需 | 说明 |
|------------|------|------|
| `ZOTERO_API_KEY` | ✅ | [Zotero API 密钥](https://www.zotero.org/settings/keys) |
| `ZOTERO_USER_ID` | ✅ | Zotero 用户 ID（在 API 密钥页面可见） |
| `VOYAGE_API_KEY` | ✅ | [Voyage AI API 密钥](https://dash.voyageai.com/) |
| `CROSSREF_MAILTO` | 推荐 | 你的邮箱，用于 Crossref 礼貌池 |
| `OPENROUTER_API_KEY` | 可选 | [OpenRouter API 密钥](https://openrouter.ai/keys)，用于 AI 摘要 |
| `MOONSHOT_API_KEY` | 可选 | [Kimi API 密钥](https://platform.moonshot.cn/)，用于 AI 摘要（与 OpenRouter 二选一） |

### 3. 启用 GitHub Pages

1. 进入 **Settings → Pages**
2. **Source** 选择 **GitHub Actions**
3. 保存设置

### 4. 首次运行

1. 进入 **Actions** 标签页
2. 点击左侧 **Daily Watch & RSS**
3. 点击 **Run workflow** 手动触发首次运行
4. 首次运行约需 5-10 分钟（构建画像 + 安装浏览器）

### 5. 访问结果

运行成功后，可通过以下地址访问：

- **RSS 订阅**：`https://[username].github.io/ZotWatch/feed.xml`
- **HTML 报告**：`https://[username].github.io/ZotWatch/report.html`

### 6. 自动运行

- Workflow 默认每天北京时间 **6:05** 自动运行
- 可在 `.github/workflows/daily_watch.yml` 中修改 cron 表达式调整时间
- 支持随时手动触发

### 运行时间说明

| 阶段 | 首次运行 | 后续运行 |
|------|---------|---------|
| 依赖安装 | ~1 分钟 | ~10 秒（有缓存） |
| Camoufox 安装 | ~2 分钟 | ~10 秒（有缓存） |
| 画像构建 | ~3-5 分钟 | 跳过（有缓存） |
| 候选抓取 + 评分 | ~2-3 分钟 | ~2-3 分钟 |
| **总计** | **~10 分钟** | **~3-5 分钟** |

## 常见问题

**Q: 如何强制重新计算所有嵌入？**
```bash
uv run zotwatch profile --full
```

**Q: 推荐为空？**

检查是否所有候选都超出 7 天窗口或预印本比例被限制。可调节 `--top` 参数或修改 `config.yaml` 中的阈值。

**Q: AI 摘要不生成？**

确保 `OPENROUTER_API_KEY` 已配置，且 `config.yaml` 中 `llm.enabled: true`。

**Q: 如何禁用 AI 摘要？**

在 `config/config.yaml` 中设置 `llm.enabled: false`。

## License

MIT
