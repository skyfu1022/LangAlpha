---
name: factor-miner
description: Alpha factor mining with Ralph Loop self-evolution. Mine, evaluate, and manage formulaic alpha factors using phandas operator library.
---

# FactorMiner Skill

## 1. 概述

FactorMiner 是一个 Alpha 因子挖掘 skill，用于在 A 股市场中系统性地发现、评估和管理公式化 Alpha 因子。它基于 phandas 算子库构建因子表达式，通过 IC（Information Coefficient）评估因子预测能力，并利用 Experience Memory 实现自我进化的 Ralph Loop 挖掘流程。

核心能力：
- 使用 phandas 算子组合生成因子表达式
- 通过 IC 评估管道批量验证因子有效性
- 将高质量因子持久化到因子库
- 利用 Experience Memory 指导挖掘方向，避免重复和已知无效路径

## 2. 激活方式

FactorMiner 通过以下方式激活：

- **Slash Command**：用户输入 `/factor-miner` 作为主入口，触发因子挖掘流程
- **SkillsMiddleware 注入**：SkillsMiddleware 在 system message 中注入当前可用 skill 清单。当 Agent 判断需要因子挖掘能力时，会主动读取本 SKILL.md，随后 middleware 加载对应的 host tools（`admit_factor`、`list_factors`、`get_factor_memory`、`update_factor_memory`）
- 这不是关键词自动加载机制，而是 Agent 根据任务需求主动选择加载

## 3. 可用 Tools

FactorMiner 提供 4 个 host tool，由 SkillsMiddleware 按需加载：

### 3.1 `admit_factor`

将评估通过的因子写入因子库。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | str | 是 | 因子名称（如 `"F001_momentum_5d"`） |
| `formula` | str | 是 | 因子表达式（如 `rank(ts_delta($close, 5))`） |
| `category` | str | 否 | 因子分类（如 `"momentum"`, `"volatility"`） |
| `ic_mean` | float | 是 | IC 均值（绝对值） |
| `icir` | float | 否 | ICIR 值 |
| `max_corr` | float | 否 | 与已有因子的最大截面相关性 |
| `evaluation_config` | dict | 是 | 评估配置（应至少包含 universe/symbols, start_date, end_date, forward_return_days 之一） |
| `parameters` | dict | 否 | 因子参数字典；无参数时传 `{}` |

入库条件：`|IC| >= 0.03` 且 `max_corr < 0.5`

### 3.2 `list_factors`

列出因子库中已入库的因子。无参数，返回全部因子，按 `created_at` 升序排列。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| 无 | - | - | 返回当前工作区全部已入库因子 |

### 3.3 `get_factor_memory`

读取 Experience Memory，获取历史挖掘经验（推荐方向、禁止方向、洞察等）。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| 无 | - | - | 返回完整的 Experience Memory JSON |

### 3.4 `update_factor_memory`

更新 Experience Memory，写入新一轮挖掘后的经验总结。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `memory_patch` | dict | 是 | 要合并的记忆内容，可包含以下字段 |

`memory_patch` 内部结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| `recommended` | list[dict] | 推荐模式列表，每条含 `pattern`, `description`, `example_formula` |
| `forbidden` | list[dict] | 禁止方向列表，每条含 `direction`, `description`, `correlated_with` |
| `insights` | list[str] | 洞察字符串列表 |
| `recent_logs` | list[dict] | 日志列表，每条含 `batch`, `candidates`, `passed_ic`, `passed_corr`, `admitted` |

## 4. 算子库文档

phandas 提供以下算子，用于构建因子表达式。使用方式：`import phandas as ph`。

### 4.1 算术运算（Arithmetic）

| 算子 | 说明 | 示例 |
|------|------|------|
| `+` `-` `*` `/` | 四则运算 | `$close / $open` |
| `log(x)` | 自然对数 | `log($volume)` |
| `sqrt(x)` | 平方根 | `sqrt($close)` |
| `power(x, n)` | 幂运算 | `power($returns, 2)` |
| `signed_power(x, n)` | 保留符号的幂运算 | `signed_power($returns, 0.5)` |
| `sign(x)` | 符号函数 | `sign($close - $open)` |
| `inverse(x)` | 取倒数 | `inverse($close)` |
| `where(cond, x, y)` | 条件选择 | `where($close > $open, 1, -1)` |

### 4.2 统计运算（Statistical）

| 算子 | 说明 | 示例 |
|------|------|------|
| `ts_mean(x, d)` | 滚动均值 | `ts_mean($close, 20)` |
| `ts_std_dev(x, d)` | 滚动标准差 | `ts_std_dev($returns, 20)` |
| `ts_skewness(x, d)` | 滚动偏度 | `ts_skewness($returns, 20)` |
| `ts_kurtosis(x, d)` | 滚动峰度 | `ts_kurtosis($returns, 20)` |

### 4.3 时序运算（Time-series）

| 算子 | 说明 | 示例 |
|------|------|------|
| `ts_delay(x, d)` | 滞后 d 期 | `ts_delay($close, 5)` |
| `ts_delta(x, d)` | 变化量（x - delay(x, d)） | `ts_delta($close, 5)` |
| `ts_rank(x, d)` | 滚动百分位排名 | `ts_rank($volume, 20)` |
| `ts_max(x, d)` | 滚动最大值 | `ts_max($high, 20)` |
| `ts_min(x, d)` | 滚动最小值 | `ts_min($low, 20)` |
| `ts_arg_max(x, d)` | 最大值所在位置 | `ts_arg_max($close, 20)` |
| `ts_arg_min(x, d)` | 最小值所在位置 | `ts_arg_min($close, 20)` |

### 4.4 截面运算（Cross-sectional）

| 算子 | 说明 | 示例 |
|------|------|------|
| `rank(x)` | 截面百分位排名 | `rank($close)` |
| `zscore(x)` | 截面 Z-score 标准化 | `zscore($volume)` |
| `normalize(x)` | 截面归一化（和为 1） | `normalize($volume)` |
| `mean(x)` | 截面均值 | `mean($close)` |
| `median(x)` | 截面中位数 | `median($close)` |
| `scale(x)` | 截面缩放（和的平方根为 1） | `scale($close)` |

### 4.5 平滑运算（Smoothing）

| 算子 | 说明 | 示例 |
|------|------|------|
| `ts_decay_linear(x, d)` | 线性衰减加权均值 | `ts_decay_linear($returns, 10)` |
| `ts_decay_exp_window(x, d, factor)` | 指数衰减加权均值 | `ts_decay_exp_window($close, 10, 0.5)` |

### 4.6 回归运算（Regression）

| 算子 | 说明 | 示例 |
|------|------|------|
| `ts_regression(y, x, d, lag, rettype)` | 时序回归，rettype 可选 `slope`、`Rsquare`、`residual` | `ts_regression($close, $volume, 20, 0, "slope")` |

### 4.7 相关性运算（Correlation）

| 算子 | 说明 | 示例 |
|------|------|------|
| `ts_corr(x, y, d)` | 滚动 Pearson 相关系数 | `ts_corr($close, $volume, 20)` |
| `ts_covariance(x, y, d)` | 滚动协方差 | `ts_covariance($close, $volume, 20)` |

## 5. 数据字段

因子表达式中使用 `$` 前缀引用行情数据字段：

| 字段 | 说明 |
|------|------|
| `$open` | 开盘价 |
| `$high` | 最高价 |
| `$low` | 最低价 |
| `$close` | 收盘价 |
| `$volume` | 成交量（手） |
| `$amount` / `$amt` | 成交额（元） |
| `$vwap` | 成交均价（amount / volume） |
| `$returns` | 日收益率（close / prev_close - 1） |

## 6. 因子表达式格式

因子表达式是由 phandas 算子和数据字段组合而成的字符串，遵循以下语法规则：

**基本格式**：`算子(数据字段, 参数)` 或 `算子(因子表达式, 参数)`

**示例**：

```
rank(ts_delta($close, 5))
```

含义：对收盘价 5 日变化量做截面排名。

**更多示例**：

```
# 动量因子
-ts_delta($close, 10) / $close

# 成交量异动
rank($volume / ts_mean($volume, 20))

# 波动率因子
ts_std_dev($returns, 20)

# 量价背离
ts_corr(rank($close), rank($volume), 10)

# 高级：回归残差
ts_regression($close, $volume, 20, 0, "residual")

# 条件因子
where($close > ts_mean($close, 20), $volume, -$volume)
```

**语法规则**：
- 数据字段以 `$` 开头
- 算子支持嵌套调用
- 数值参数直接写数字
- 截面算子（rank, zscore 等）不需要窗口参数
- 时序算子需要窗口参数 `d`（整数）
- `where` 三元算子格式：`where(条件, 真值, 假值)`

## 7. 评估管道

因子评估管道包含三个阶段：

### 7.1 IC 计算

IC（Information Coefficient）衡量因子值与未来收益率的预测关系：

- **方法**：Spearman 秩相关系数
- **截面计算**：每个交易日对所有股票计算因子值与下一期收益率之间的 Spearman rank correlation
- **时间聚合**：对所有截面的 IC 取均值和标准差
- **ICIR**：`ICIR = mean(IC) / std(IC)`，衡量 IC 的稳定性

### 7.2 IC 筛选

因子必须满足以下条件才考虑入库：

- `|IC_mean| >= 0.03`：IC 均值绝对值不低于 0.03
- `ICIR` 越高越好，反映预测能力的稳定性

### 7.3 相关性检查

新因子与因子库中已有因子的截面相关性必须满足：

- `max_corr < 0.5`：新因子与每个已有因子的截面相关系数的最大值低于 0.5
- 计算方式：在每个截面上计算新因子与已有因子的 Pearson 相关，取时间序列上的均值

## 8. Ralph Loop 流程

FactorMiner 使用 Ralph Loop 实现自我进化的因子挖掘：

```
┌─────────────────────────────────────────┐
│  1. 读取记忆                             │
│     get_factor_memory()                  │
│     获取 recommended / forbidden / insights │
├─────────────────────────────────────────┤
│  2. 生成候选因子                          │
│     基于记忆和算子库生成一批候选因子表达式   │
├─────────────────────────────────────────┤
│  3. 批量评估                             │
│     在 Sandbox 中执行评估代码             │
│     计算 IC、ICIR、相关性                  │
├─────────────────────────────────────────┤
│  4. 入库                                 │
│     对通过筛选的因子调用 admit_factor()     │
├─────────────────────────────────────────┤
│  5. 记忆蒸馏                             │
│     分析本轮结果，提炼经验                 │
│     update_factor_memory()               │
└─────────────────────────────────────────┘
```

每轮挖掘后，记忆更新会指导下一轮的搜索方向——强化有效路径、规避无效路径，实现迭代进化。

## 9. Experience Memory 管理

Experience Memory 是 FactorMiner 自我进化的核心数据结构，通过 `get_factor_memory()` 读取、`update_factor_memory()` 更新。

### 9.1 数据结构

```json
{
  "recommended": [
    {"pattern": "量价背离", "description": "量价背离类因子在短期窗口表现较好", "example_formula": "ts_corr(rank($close), rank($volume), 10)"},
    {"pattern": "rank_ts", "description": "截面排名后的时序运算稳定性高", "example_formula": "rank(ts_mean($returns, 10))"}
  ],
  "forbidden": [
    {"direction": "纯价格动量", "description": "纯价格动量因子与已有因子高度相关", "correlated_with": "rank(ts_delta($close, 5))"},
    {"direction": "长窗口均值", "description": "超过 60 日窗口的均值因子 IC 不显著", "correlated_with": ""}
  ],
  "insights": [
    "小市值股票因子 IC 波动较大，需注意样本偏差",
    "成交量相关因子在市场异动期表现不稳定"
  ],
  "recent_logs": [
    {"batch": 3, "candidates": 20, "passed_ic": 8, "passed_corr": 3, "admitted": 3},
    {"batch": 2, "candidates": 15, "passed_ic": 5, "passed_corr": 1, "admitted": 1}
  ]
}
```

### 9.2 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `recommended` | list[dict] | 推荐模式列表，每条含 `pattern`(模式名)、`description`(说明)、`example_formula`(示例表达式)，上限 10 条 |
| `forbidden` | list[dict] | 禁止方向列表，每条含 `direction`(方向名)、`description`(说明)、`correlated_with`(关联因子)，上限 15 条 |
| `insights` | list[str] | 从挖掘过程中提炼的通用洞察，上限 15 条 |
| `recent_logs` | list[dict] | 最近几轮挖掘日志，每条含 `batch`/`candidates`/`passed_ic`/`passed_corr`/`admitted`，上限 20 条 |

### 9.3 更新规则

- 每轮挖掘结束后调用 `update_factor_memory`
- `recommended` 总量不超过 10 条，超出时淘汰最早的条目
- `forbidden` 总量不超过 15 条，超出时淘汰最早的条目
- `insights` 总量不超过 15 条，超出时淘汰最早的条目
- `recent_logs` 只保留最近 20 条

## 10. 挖掘策略

在每轮挖掘中，应参考 Experience Memory 调整策略：

### 10.1 推荐方向

根据 `recommended` 中记录的有效模式，优先探索：
- recommended 中提到的算子组合方式
- 之前成功的因子结构的变体（调整窗口参数、替换相似算子）
- recommended 中提到的数据字段组合

### 10.2 禁止方向

根据 `forbidden` 中记录的无效模式，避免：
- forbidden 中明确指出无效的算子组合
- 与已有因子高度相关的因子结构
- IC 历史表现不稳定的方向

### 10.3 探索策略

- **广度优先**：每轮生成 15-25 个候选因子，覆盖不同算子类别和数据字段
- **深度渐进**：对表现好的因子结构，在后续轮次中探索参数变体
- **正交性优先**：优先探索与因子库中已有因子低相关的方向
- **多样性保证**：每轮候选应包含不同类型的因子（动量、波动率、成交量、量价关系等）
