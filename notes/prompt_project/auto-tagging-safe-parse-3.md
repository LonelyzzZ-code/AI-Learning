# 笔记自动打标签·JSON 输出兜底实录（02 模块 · 任务 3）

> 日期：2026-10-13
> 对象：`code/Function Calling-1.py`——读 `File/01-LLM-API三件套.md` 和 `File/02-Prompt工程.md`，让 AI 输出 `{title, tags, summary}`，`response_format` JSON mode + safe_parse 兜底，结果存 JSON（03 号 RAG 入库打标签的预演）
> 最终结果：跑通 ✅，"删 response_format 验证兜底"实验完成 ✅。核心主题一句话：**怎么让 AI 的输出能被程序可靠地解析**

```
读 .md → 发给 AI（system：只输出 JSON + response_format）→ safe_parse
         ├─ json.loads 一次成功 → 直接用
         └─ 失败 → 坏输出以 assistant 身份喂回 + 纠正指令 → 再调一次 create() → 二次 loads
两篇都完成 → results 攒起来 → json.dump 一次写盘
```

## 版本迭代史总览

| 版本 | 现象 | 根因 | 对应知识点 |
| ---- | ---- | ---- | ---------- |
| v1 | except 里拼完 messages 就停了 | 以为"拼接 = 重试" | 自修复重试的完整三步 |
| v1 | （潜在）第二篇请求串台 | 外层 messages 被改写 | 传参 vs 赋值、模板/会话分离 |
| v2 | except 一触发就 NameError | `base_massages` 拼写不一致 | 没被执行过的兜底 = 没验证过的代码 |
| v3 | `NameError: results` | 字典没初始化 + 该行缩进在循环外 | 创建字典 ≠ 往里加项 |
| v4 | 全部跑通 | —— | —— |

## v1 的 4 个硬伤

```python
# ① load 吃文件对象，loads 吃字符串（惯犯第 2 次，第一次在 FC 解析 arguments）
data = json.load(resp)          # ✗ AttributeError
data = json.loads(resp)         # ✓

# ② except 里只拼了重试 messages，没有真正再调 create()
#    重试的灵魂三步：坏输出喂回去 → 重新请求 → 二次解析，缺一不可

# ③ 跨循环污染（见下节，本任务最大的结构问题）

# ④ role 拼成 "assisant"（惯犯第 2 次，10-09 text1.py 同款）
{"role": "assisant", ...}       # ✗ API 直接 400
```

### 重点展开：③ 跨循环污染是怎么发生的

前置知识——两个长得一模一样、但完全不同的 `messages =`：

```python
response = client.chat.completions.create(
    messages = messages + [user],   # 括号内：关键字传参，新列表递给 create 用完就扔，外层变量不变
)
messages = messages + [...]         # 顶格：赋值语句，永久改写外层变量
```

再加一条：**Python 的 for / except 没有块作用域**，循环体内赋值的变量会活到下一轮。两者叠加：

```
第 1 篇：create 收到 [S, U1] → 解析失败 → except 里顶格赋值
         messages = [S, A坏, C纠]           ← 外层被改写
第 2 篇：create 收到 [S, A坏, C纠, U2]      ← 第一篇的尸体混进来了
```

后果：模型看到"我之前输出过一段坏 JSON、被要求修正、然后又来了一篇新文章"——可能去修旧输出、可能两篇混着总结，且垃圾随失败次数越滚越大。

**修正口诀：模板 / 会话分离。**

- `system_messages` = 模板，**永不动它**
- `msgs = system_messages + [本篇 user]` = 一次性会话，循环内现拼、用完就扔
- 重试 = 扩展这份局部 `msgs`，只是"这个聊天窗口里的第二次发言"，绝不回头改模板

## v2：一个只有验证实验才能炸出来的 NameError

```python
base_massages = system_messages + [...]   # 定义时拼错（massages）
base_messages = base_messages + [...]     # 使用时正确 → except 触发即 NameError
```

这个 bug 最阴险的地方：**开着 response_format 时解析基本不会失败，except 永远不走，你根本发现不了它**。只有按任务要求删掉 response_format 做验证实验时，它才会爆——这正是"验证兜底"环节存在的意义：**没被执行过的兜底代码，等于没验证过的代码**（拼写、未定义变量、错误的变量名全可能藏在里面）。

## v3：`NameError: results`——两个问题叠加

1. **字典必须先创建**：`results = {}` 是创建字典，`results[path] = ...` 是往已存在的字典里加一项——后者以前者为前提，Python 不会自动建
2. **缩进在循环外**：顶格的 `results[path] = ...` 循环结束后只执行一次，只有最后一篇的结果被存进去，第一篇丢了

### 顺带弄懂的两段代码

**`data.get(key, 默认值)` 白名单清洗**——response_format 只保证"是合法 JSON"，不保证字段齐全（模型可能合法地返回 `{"title": "xx"}`，tags 没了）：

```python
results[path] = {                    # 右边 = 字典字面量，现造一个白名单
    "title":   data.get("title", ""),    # 缺 → KeyError ✗
    "tags":    data.get("tags", []),     # get(key, 默认值)：缺字段返回默认值，永不崩
    "summary": data.get("summary", ""),
}
# 不管 AI 多给/少给什么字段，落盘结构永远固定 3 个字段 = 数据归一化
```

**默认值的类型一致性**——默认值必须和字段本来的类型一致，下游才能闭着眼睛用：

```python
tags = data.get("tags", [])   # → []    for t in tags: 循环 0 次，安全 ✅
tags = data.get("tags")       # → None  for t in tags: TypeError ❌
tags = data.get("tags", "")   # → ""    for t in tags: 逐字符遍历，不报错但结果错 ❌
```

口诀：列表给 `[]`、字符串给 `""`、字典给 `{}`、数字给 `0`。

**写盘**（循环外，收集完一次写）：

```python
with open("code/tags.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
# ensure_ascii=False：中文原样写入（否则全变 \uXXXX）；indent=2：只是好看
```

写文件缩进在循环内不是错误（最后一次覆盖，结果碰巧一样），但每篇写一次盘纯属浪费——100 篇就写 100 次。

## v4：验证兜底实验

1. 注释掉 `response_format` 再跑 → 模型输出带 ```` ```json ```` 包裹/前后废话 → 第一次 `json.loads` 失败
2. except 触发：坏输出以 assistant 身份喂回 + "上面的输出不是合法JSON，请严格只输出JSON" → 再调 create() → 二次解析成功
3. 亲眼确认"先失败 → 重试 → 接住"，证明兜底不是永不执行的摆设

**实验态 vs 标准态**（验证完要不要恢复 response_format）：

- `response_format` = 保险（语法层预防，免费）
- `safe_parse` = 安全气囊（失败了自修复）
- 标准态两层都装：首次就开 response_format，绝大多数一次成功，except 退化成备胎
- 保留实验态（首次不开、重试才开）代码照样正确，代价是模型每次抽风都多烧一次重试调用

实际输出节选（glm-4-flash）：

```json
"File/01-LLM-API三件套.md": {
  "title": "LLM API 三件套：对话 / 流式 / Function Calling",
  "tags": ["AI", "API", "ChatGPT", "Function Calling", "SSE", "Stream", "OpenAI"],
  "summary": "本文介绍了LLM API的三件套：对话、流式输出和Function Calling……"
}
```

## 惯犯清单（第 2 次出现，重点盯防）

| 惯犯 | 第 1 次 | 第 2 次（本次） |
| ---- | ------- | -------------- |
| `json.load` / `json.loads` 混用 | FC 解析 arguments | 解析模型输出 |
| role 拼成 `assisant` | text1.py | 重试 messages |

## 方法论沉淀（面试可用）

1. **response_format 只保证合法 JSON，不保证字段齐全** → 下游取值一律 `dict.get(key, 类型一致的默认值)`，白名单重建固定结构
2. **模板/会话分离**：固定 system 模板永不改，每篇输入现拼一次性 msgs；重试是会话内的第二次发言，不是改模板
3. **括号内 `xx =` 是传参，顶格 `xx =` 才是赋值**——判读别人的代码先分清这两者
4. **兜底代码必须被真实验证过**：藏在 except 里的拼写/NameError，正常路径永远踩不到；故意制造一次失败（删 response_format）是唯一暴露手段
5. **上游不可信，落盘前归一化**：AI 输出是"不可信输入"，写文件/给下游前先清洗成固定结构
6. **收集完一次性写盘**，别在循环里反复 open/write
7. 错误兜底只重试一次（与笔记 safe_parse 一致）；生产环境再加"重试上限 + 最终默认值"
