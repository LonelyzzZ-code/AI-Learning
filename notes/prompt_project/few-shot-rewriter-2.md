# Few-shot 查询改写器踩坑实录（02 模块 · 任务 2）

> 日期：2026-10-12
> 对象：`code/prompt_project.py` 的 `rewrite(question)`——把口语问题改写成搜索关键词（03 号 RAG 检索环节直接复用）
> 最终结果：5 个测试问法全部合格。这篇记的是从 v1 到 v5 的完整翻车链，每一版一个独立知识点。

## 版本迭代史总览

| 版本 | 现象 | 根因 | 对应知识点 |
| ---- | ---- | ---- | ---------- |
| v1 | 直接报错 | 3 个 bug 叠加 | Python 基础 × API 返回结构 |
| v2 | 零输出 | `messages = None` | `append` 返回 None |
| v3 | 输出为空 | 思考烧光 token 预算 | 思考型模型 × max_tokens |
| v4 | 2/5 跑偏 | few-shot 压不住求助式问法 | 示例覆盖度 |
| v5 | 5/5 ✅ | —— | 负面约束 + 失败样例反哺 |

## v1：三处硬伤（还没跑就错了）

```python
# bug ①：append 返回 None，等价于 messages = None
messages = lizis.append(question)
# bug ②：question 定义成了列表套字典，拼进 messages 变嵌套列表
question = [{"role": "user", "content": "..."}]
# bug ③：content 不在 choices[0] 这一层上
resp = response.choices[0].content        # ✗ 少了 .message
```

- 口诀：`append` / `sort` / `reverse` 都是"**原地修改、返回 None**"——要拼新列表永远用 `+`
- 取回复永远是两层：`choices[0].message.content`
- few-shot 模板列表要当作**只读常量**，请求时用 `模板 + [真实问题]` 拼新列表，否则多次调用会污染示例

## v2：append 又背了一次锅

改了 ②③，唯独 ① 没改 → `messages=None` → 服务端 400，`print` 一行都执行不到。

教训：**"零输出"先翻终端里的 traceback**（openai.BadRequestError 就躺在那），别盯着 print 语句找原因。

## v3：输出全是空——思考型模型的 max_tokens 陷阱

把模型换成 `glm-5.3-flash` 后，`content` 变成空字符串（print 出来"："后面是**空**，不是 None——这是"答案压根没开始写"的形状）。

机制：思考型模型先往 `reasoning_content` 字段打草稿，再往 `content` 写正式答案，**两段共用同一个 max_tokens 预算**。`max_tokens=32` 被思考过程烧光，答案一个字没轮到（`finish_reason == "length"`）。

修复二选一：

```python
# ① 关思考（推荐）：简单任务不需要推理
extra_body = {"thinking": {"type": "disabled"}}

# ② 放水：max_tokens 提到 512 让它想完——慢且费 token
```

对应正文 §2③"简单任务不要 CoT"：手写的 CoT 和模型自带的思考模式，结论一样——改写/抽取/分类这类一步到位的任务，关掉。

## v4：2/5 跑偏——求助式问法压不住

换回 `glm-4-flash` 后有输出了，但：

- "咋用redis加速" → 模型**当真问题回答了**（输出 Redis 使用教程）
- "网页加载慢咋排查" → 多了"关键词："前缀和编号列表

根因：system 只有一句正面指令（"把用户问题改写成搜索关键词"），**没禁止"回答问题"**；2 个示例里也没有求助式问法的样本。

立功细节：`max_tokens=32` 把跑偏的长输出拦腰截断——**硬闸在输出跑偏时负责止损**，这正是它的职责。

## v5：两处药方 → 5/5

```python
FEW_SHOT_MESSAGES = [
    {"role": "system", "content": """把用户的问题改写成搜索关键词。
规则：只输出 2~4 个关键词，用空格分隔；
不要回答问题，不要解释，不要编号，不要加"关键词："之类的前缀。"""},
    {"role": "user", "content": "那篇讲数据库索引的文章叫啥"},
    {"role": "assistant", "content": "数据库 索引"},
    {"role": "user", "content": "怎么用redis做缓存"},
    {"role": "assistant", "content": "Redis 缓存"},
    # 第 3 个示例：就用 v4 刚翻车的"求助式问法"
    {"role": "user", "content": "网页打开很卡怎么排查"},
    {"role": "assistant", "content": "前端 性能优化"},
]
```

1. **负面约束具体化**：不要回答问题/解释/编号/加前缀（§2① 的"负面约束要具体"）
2. **示例 2→3**，新增的一组**直接采用失败问法的类型**——"网页打开很卡怎么排查 → 前端 性能优化"

最终 5/5 输出全部是"词 + 空格"格式。

## 方法论沉淀（面试可用）

1. **失败样例是最好的 few-shot 素材**：哪个输入跑偏，就把它配上正确输出做成第 N+1 个示例——示例集是用失败喂出来的
2. **负面约束要具体**："不要 X、不要 Y" 比 "要简洁规范" 有效得多
3. **prompt 是软约束，max_tokens 是硬闸**：格式靠 prompt 劝，失控靠 max_tokens 掐
4. **思考型模型的输出预算 = 思考 + 答案**：小 max_tokens 会饿死答案；简单任务直接 `thinking: disabled`
5. **排障顺序**：零输出看 traceback → 空输出查 `finish_reason` → 格式跑偏改 prompt（加负面约束/加示例）
