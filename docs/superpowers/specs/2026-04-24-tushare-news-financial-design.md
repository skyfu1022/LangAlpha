# TuShare 新闻资讯与财务报表数据源设计

**日期：** 2026-04-24
**状态：** 已修订
**范围：** 在现有 data_client 架构中扩展 TuShare，新增新闻资讯和财务报表两个数据领域，供中国市场优先使用。

## 1. 背景与目标

### 现状

- TuShare 已实现 A 股行情数据（`MarketDataSource`）：日线、分钟线、ETF、指数、股票基本信息、财报披露日期
- 新闻数据由 ginlix-data、FMP、yfinance 提供，**不支持中国市场新闻**
- 财务数据由 FMP、yfinance 提供，**无中国市场专业财务数据**
- Agent（通过 MCP）和前端（通过 REST API）均无法获取中国市场的新闻和财务数据

### 目标

- TuShare 作为中国市场新闻和财务数据的首选数据源
- 复用现有协议驱动架构，接入 provider chain 和 fallback 机制
- Agent 和前端均可使用新数据

## 2. 方案选择

**选定：完整协议实现（方案 A）**

在 `src/data_client/tushare/` 中扩展，实现 `NewsDataSource` 和 `FinancialDataSource` 协议接口。MCP server 调用 data_client 而非直接调用 TuShare API，避免代码重复。

**排除方案：**
- 仅扩展 MCP Server（前端无法使用）
- 独立新模块（重复代码，不走 fallback chain）
- MCP 直接调用 TuShare（与 data_client 重复，yfinance 模式存在此技术债）

## 3. 架构设计

### 3.1 文件变更清单

```
src/data_client/
├── tushare/
│   ├── client.py                    # 扩展：增加新闻 + 财务 API 方法
│   ├── data_source.py               # 已有：行情（不动）
│   ├── news_data_source.py          # 新增：NewsDataSource 实现
│   └── financial_data_source.py     # 新增：FinancialDataSource 实现
├── news_data_provider.py            # 修改：保留 markets 元数据，按 market 路由
├── financial_data_provider.py       # 修改：按 symbol/market 路由 + unsupported fallback 语义
└── registry.py                      # 修改：注册新 source

src/config/
├── models.py                        # 修改：新增 FinancialDataConfig
└── settings.py                      # 修改：增加 get_financial_data_providers()

src/server/app/
└── news.py                          # 修改：market 透传给 NewsDataProvider 做 source 选择

config.yaml                          # 修改：news_data 增加 markets；新增 financial_data.providers

mcp_servers/
└── tushare_price_mcp_server.py      # 扩展：增加新闻和财务工具
```

### 3.2 数据流

```
前端 REST API  ←→  FastAPI Router  ←→  Data Provider (chain/fallback)
                                                ↕
Agent (MCP)    ←→  MCP Server Tools  ←→  TuShare Data Sources
                                                ↕
                                          TuShareClient (HTTP)
                                                ↕
                                        api.tushare.pro (Pro API)
```

关键设计：MCP server 调用 data_client 中的 data source 类的公共方法，不直接调用 TuShareClient。所有 TuShare API 调用和字段映射逻辑只有一份。

### 3.3 共享 TuShareClient

所有 data source 共享同一个 `TuShareClient` 单例（复用现有的 `get_tushare_client()`），统一 token 认证和连接管理。

### 3.4 与现有 Provider 架构对齐

- **新闻 provider 不能只改 YAML**：当前 `NewsDataProvider` 仅按顺序 fallback，不识别 `markets`。本次需要把 `news_data.providers[*].markets` 保留到运行时，在 provider 层按 `market` 先筛 source，再执行 fallback。
- **新闻 market 由 router 显式透传**：`GET /api/v1/news?market=cn` 已有 `market` 参数，但当前只用于结果过滤。修订后 `src/server/app/news.py` 需要把 `market` 一并传给 `provider.get_news(...)`，用于 source 选择；具体 data source 接口保持不变。
- **财务 provider 需要补 config plumbing**：当前 `get_financial_data_provider()` 是硬编码装配 FMP/yfinance/ginlix-data，不读取 YAML。修订后新增 `financial_data.providers` 配置，并在 `src/config/models.py`、`src/config/settings.py`、`src/data_client/registry.py` 中完整接线。
- **financial / intel 继续分层**：`FinancialDataProvider` 仍保持 `financial` 与 `intel` 双通道结构。本 spec 仅让 `provider.financial` 变为 config-driven + market-aware；`provider.intel` 继续沿用现有 ginlix-data 装配方式，不与 `financial_data.providers` 混合。

## 4. TuShare Client 扩展

在 `client.py` 中新增以下 API 方法，均为 `query_dataframe()` 的轻量封装：

### 4.1 新闻资讯 API

| 方法 | TuShare 接口 | 说明 |
|---|---|---|
| `news(src, start_date, end_date)` | `news` | 7x24 财经新闻 |
| `major_news(type, start_date, end_date)` | `major_news` | 长篇通讯/深度报道 |
| `cctv_news(date)` | `cctv_news` | 新闻联播文字稿 |
| `news_content(id)` | `news_content` | 单篇新闻详情 |

### 4.2 财务报表 API

| 方法 | TuShare 接口 | 说明 |
|---|---|---|
| `income(ts_code, period, start_date, end_date)` | `income` | 利润表 |
| `balancesheet(ts_code, period, start_date, end_date)` | `balancesheet` | 资产负债表 |
| `cashflow(ts_code, period, start_date, end_date)` | `cashflow` | 现金流量表 |
| `financial_indicator(ts_code, period, start_date, end_date)` | `fina_indicator` | 财务指标 |
| `fina_forecast(ts_code, period)` | `fina_forecast` | 业绩快报/预告 |
| `disclosure_date(ts_code, period)` | `disclosure_date` | 财报披露日期（已有） |

## 5. 新闻资讯 Data Source

### 5.1 `TuShareNewsDataSource` — 实现 `NewsDataSource` 协议

**`get_news(tickers, limit, published_after, published_before, cursor, order, sort, user_id)`：**

- 无 tickers 时调用 `news()` 获取 7x24 财经快讯
- 有 tickers 时获取全量新闻，在返回结果中按股票名称/代码关键词过滤（TuShare news 接口不支持按个股过滤，此为已知限制，个股过滤结果可能不完整）
- `published_after/before` 映射为 TuShare 的 `start_date/end_date`
- `limit` 控制返回条数（默认 20，上限 100）
- `cursor` 改为**不透明游标**，编码 `{published_at, article_id}`，避免直接暴露分页细节
- 分页语义固定为**按时间倒序**：下一页使用 `published_before/end_date = cursor.published_at` 继续拉取，而不是 `start_date=cursor`
- 为处理“相同发布时间多条新闻”的边界，data source 需要在本地按 `(published_at, article_id)` 去重，并过滤掉上一页边界记录后再裁剪到 `limit`
- `order` 默认按时间倒序
- 返回格式：`{results: [...], count: int, next_cursor: str|None}`
- 每条结果映射为统一 News API schema：`{id, title, description, article_url, published_at, source: {name, ...}, tickers, image_url, keywords, sentiments}`

**`get_news_article(article_id, user_id)`：**

- 调用 `news_content(id)` 获取全文
- 返回完整文章详情

### 5.2 Provider 注册 — CN 市场首选

```yaml
news_data:
  providers:
    - name: ginlix-data
      markets: [us]
    - name: tushare
      markets: [cn]        # CN 市场首选
    - name: fmp
      markets: [all]       # fallback
    - name: yfinance
      markets: [all]       # fallback
```

运行时设计：

- `NewsDataProvider` 改为保存 `ProviderEntry(name, source, markets)`，而不是简单的 `(name, source)` 元组
- `registry.py` 在构建 news provider 时，必须把 `config.yaml` 中的 `markets` 原样带入 entry
- `provider.get_news(..., market="cn")` 时只尝试 `markets` 包含 `cn` 或 `all` 的 source；`market="us"` 同理
- 当 `market` 为空时，保持现有顺序 fallback 行为
- 市场路由结果：CN 市场 → TuShare 优先，失败 fallback 到 fmp/yfinance；US 市场 → ginlix-data 优先

## 6. 财务报表 Data Source

### 6.1 `TuShareFinancialDataSource` — 实现 `FinancialDataSource` 协议

**协议方法映射：**

| 协议方法 | TuShare API | 说明 |
|---|---|---|
| `get_income_statements()` | `income()` | 利润表 |
| `get_cash_flows()` | `cashflow()` | 现金流量表 |
| `get_financial_ratios()` | `financial_indicator()` | 财务指标（ROE、毛利率等） |
| `get_key_metrics()` | `financial_indicator()` | 最新一期关键指标 |
| `get_company_profile()` | `stock_basic()` | 公司基本信息 |
| `get_realtime_quote()` | `daily_basic()` | 当日行情指标（PE、PB 等） |

**不适用的方法（抛出 unsupported 异常，让 fallback chain 继续）：**

- `get_analyst_price_targets()` — 中国市场分析师目标价
- `get_analyst_ratings()` — 中国市场评级
- `get_price_performance()` — 价格表现
- `get_earnings_history()` — 业绩快报
- `get_revenue_by_segment()` — 分部营收
- `get_sector_performance()` — 板块表现
- `screen_stocks()` / `search_stocks()` — 条件选股

实现约束：

- 不能返回 `None` 作为“跳过当前 source”的信号，因为现有 fallback 包装器会把 `None` 视为成功返回
- 推荐做法：这些方法显式抛出 `NotImplementedError`（或项目内新增等价的 unsupported capability 异常）
- `FallbackFinancialDataSource` 需要将这类异常视为**预期 fallback**，继续尝试下一个 source，并使用较低级别日志记录，避免污染 warning

### 6.2 数据映射要点

- `symbol` 参数：从 `000001.SZ` 格式直接映射到 TuShare 的 `ts_code`
- `period` 参数：统一为 `YYYYMMDD` 格式（如 `20231231`）
- 金额字段：TuShare 返回元为单位，保持元作为单位（中国市场惯例）
- 字段名映射：TuShare 原始字段名映射到协议标准字段名

### 6.3 Provider 注册 — CN 市场首选

```yaml
financial_data:
  providers:
    - name: tushare
      markets: [cn]        # CN 财务数据首选
    - name: fmp
      markets: [all]       # fallback
    - name: yfinance
      markets: [all]       # free fallback
```

接线要求：

- 在 `src/config/models.py` 中新增 `FinancialDataConfig`，结构与 `MarketDataConfig` / `NewsDataConfig` 一致，字段为 `providers: List[MarketDataProviderConfig]`
- 在 `InfrastructureConfig` 中新增 `financial_data: FinancialDataConfig`
- 在 `src/config/settings.py` 中新增 `get_financial_data_providers()`，并提供与当前行为兼容的默认值（至少包含 `fmp`、`yfinance`）
- 在 `src/data_client/registry.py` 中重写 `get_financial_data_provider()` 的 financial 装配逻辑：按配置顺序注册 source，并保留每个 source 的 `markets`
- `FallbackFinancialDataSource` 需要基于 `symbol_market(symbol)` 或等价逻辑优先选择匹配 market 的 source；无 symbol 的方法保持顺序 fallback
- `provider.intel` 维持现有 ginlix-data 注册逻辑，不纳入本 YAML

### 6.4 Data Source 额外公共方法

除了协议方法外，`TuShareFinancialDataSource` 暴露额外公共方法供 MCP server 调用：

- `get_balance_sheet(ts_code, period)` — 资产负债表（协议中无此方法）
- `get_financial_indicator_detail(ts_code, period)` — 完整财务指标（含杜邦分析）
- `get_fina_forecast(ts_code, period)` — 业绩快报/预告
- `get_disclosure_dates(period, ts_code)` — 披露日期

## 7. MCP Server 扩展

在现有 `tushare_price_mcp_server.py` 中新增工具，调用 data_client data source 的公共方法：

### 7.1 新闻工具

| MCP 工具 | 调用目标 | 说明 |
|---|---|---|
| `get_cn_financial_news(date, limit)` | `TuShareNewsDataSource.get_news()` | 获取中国财经新闻 |
| `get_cn_news_detail(news_id)` | `TuShareNewsDataSource.get_news_article()` | 获取新闻详情 |

### 7.2 财务工具

| MCP 工具 | 调用目标 | 说明 |
|---|---|---|
| `get_cn_income_statement(ts_code, period)` | `TuShareFinancialDataSource.get_income_statements()` | 利润表 |
| `get_cn_balance_sheet(ts_code, period)` | `TuShareFinancialDataSource.get_balance_sheet()` | 资产负债表 |
| `get_cn_cashflow_statement(ts_code, period)` | `TuShareFinancialDataSource.get_cash_flows()` | 现金流量表 |
| `get_cn_financial_indicator(ts_code, period)` | `TuShareFinancialDataSource.get_financial_indicator_detail()` | 财务指标 |

## 8. 前端集成

最小改动策略，与 yfinance 模式一致：

1. **新闻**：前端 API 合约不变，仍调用 `GET /api/v1/news?market=cn`；但后端需要补上 `market -> provider routing` 透传，不能只依赖结果过滤
2. **Dashboard 新闻卡片**：如需展示 CN 新闻，根据 watchlist 自动混合展示
3. **财务数据**：Agent 侧通过 MCP 自动可用。前端暂不增加独立财务报表页面

## 9. 测试策略

- 在 `tests/unit/` 下为每个新 data source 写单元测试，mock TuShare API 响应
- 重点测试：字段映射正确性、空结果处理、新闻 provider 市场路由、financial provider config 装配、unsupported capability fallback、cursor 分页去重
- 配置测试：`financial_data.providers` 能被 `InfrastructureConfig` 正确解析；默认值保持与当前行为兼容
- 路由测试：`src/server/app/news.py` 在 `market=cn/us` 下会把 market 透传给 provider，而不仅仅是对结果做后过滤
- MCP 工具测试：验证工具注册和参数传递到 data source 方法

## 10. 实现顺序

1. 补 config plumbing：`config.yaml`、`src/config/models.py`、`src/config/settings.py`
2. 调整 provider 装配：news provider 保留 `markets`；financial provider 改为 config-driven + market-aware
3. 扩展 `client.py` — 添加所有新闻和财务 API 方法
4. 实现 `TuShareNewsDataSource` + 稳定 cursor 语义
5. 实现 `TuShareFinancialDataSource` + unsupported capability fallback 语义
6. 扩展 MCP server — 增加新闻和财务工具
7. 编写单元测试
