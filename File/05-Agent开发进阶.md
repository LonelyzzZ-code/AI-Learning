# 05 · Agent 开发进阶（分叉方向 A）

> 前置：01-04 基地全部完成（尤其 Function Calling 和 RAG——Agent = 三件套放进循环）
> 时间：寒假启动，大二下深化
> 目标岗位依据：深信服 AI Agent 开发工程师 JD（30-60k·15薪，1-3年本科）
> 💡 全模块主线只有一句话：**框架（LangChain/LangGraph/MCP）都是 01 号那个 15 行 FC 循环的包装**。每个框架先问"它替我省了哪段、又藏了哪段"，就不会迷路。

---

## 1. 知识树（按顺序）

### 第 1 层：LangChain 基础（1 周）

学它不是为了用它写生产代码，是为了看懂生态里的概念词汇。对照表（左边全部是你在 01/02 手写过的）：

| 你手写过的（01/02 号） | LangChain 的封装 | 它帮你省了什么 |
|---|---|---|
| `client.chat.completions.create(...)` | `ChatModel.invoke()` | 换模型厂商只改一个参数 |
| f-string 拼 Prompt + `prompts.py` | `PromptTemplate` | 模板变量管理 |
| `json.loads` + 校验 + 兜底重试 | `OutputParser` | 解析失败自动重试 |
| tools JSON 声明 + 执行循环 | `Tool` + `create_react_agent` | 整个 Agent 循环 |
| 自己维护 messages 数组 | `Memory` / 消息历史 | 历史截断与存储 |

```python
# 30 行看懂 LangChain：每个对象都对应你手写过的东西
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

llm = ChatOpenAI(                                  # ← 就是 01 的 client（换成智谱 base_url）
    model="glm-4-flash",
    api_key=os.environ["ZHIPU_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
prompt = ChatPromptTemplate.from_messages([        # ← 就是 02 的 messages 列表
    ("system", "你是我的知识库助手，回答控制在200字内"),
    ("user", "{question}"),                        # ← 就是 REWRITE_TEMPLATE.format()
])
chain = prompt | llm                               # ← 管道符：上一步输出接下一步输入（LCEL）
print(chain.invoke({"question": "什么是RAG"}).content)
```

📌 **LCEL（管道 `|`）**是 LangChain 的核心语法：`prompt | llm | parser` 就是一条处理链。看法：概念过一遍能说出"这层封装帮我省了什么"就够，重点在第 2 层。

### 第 2 层：LangGraph（重点，2-3 周）

深圳 JD 出现频率最高的框架。核心思想：📌 **把 Agent 建模成状态机/图**——State（状态对象）、Node（节点=一步操作）、Edge（边=下一步去哪）、条件边（按条件选路）、循环（工具节点指回模型节点）。

先看"手写循环 → 图"的翻译，这是一切的关键：

```
01 号手写 FC 循环：                  LangGraph 等价物：
─────────────────                   ──────────────
messages 数组                 →      State（状态对象，贯穿全图）
call_model()                 →      "model" 节点
if msg.tool_calls:           →      条件边 should_continue
run_tool()                   →      "tools" 节点
for 循环                     →      tools → model 的回边（循环即边）
```

最小可跑的知识库问答 Agent（逐行注释版）：

```python
# pip install langgraph langchain-openai
import os
from typing import Annotated, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# ---- 1. State：全图共享的"公告板" ----
class State(TypedDict):
    messages: Annotated[list, add_messages]
    # ← Annotated[list, add_messages] 的意思：节点返回新消息时"追加"而不是"覆盖"
    #   （add_messages 是 reducer 函数；没有它，每个节点会互相覆盖 messages）

llm = ChatOpenAI(model="glm-4-flash",
                 api_key=os.environ["ZHIPU_API_KEY"],
                 base_url="https://open.bigmodel.cn/api/paas/v4/")

# ---- 2. 工具：@tool 装饰器自动生成 01 号手写的 tools JSON ----
@tool
def search_kb(keyword: str) -> str:
    """在个人知识库（markdown 笔记）里按关键词检索，返回相关文章的标题和内容片段"""
    # ↑ docstring = 给模型看的说明书（对应01号 tools 里的 description！）
    return "《03-单链表》：单链表的结构、插入删除的实现与复杂度……"

tools = [search_kb]
llm_with_tools = llm.bind_tools(tools)     # ← 相当于请求里带上 tools 参数

# ---- 3. 节点：每个节点读 State、返回 State 的增量 ----
def call_model(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# ---- 4. 条件边：模型要工具吗 ----
def should_continue(state: State):
    last = state["messages"][-1]
    return "tools" if last.tool_calls else END    # ← 返回下一节点名或END

# ---- 5. 组装图 ----
g = StateGraph(State)
g.add_node("model", call_model)             # 模型节点
g.add_node("tools", ToolNode(tools))        # 工具节点：自动执行tool_calls并回喂（01号手写的③④步）
g.add_edge(START, "model")                  # 入口 → 模型
g.add_conditional_edges("model", should_continue)   # 模型 → tools 或 END（按条件选路）
g.add_edge("tools", "model")                # ★ 工具结果 → 回模型：循环就来自这条边！
app = g.compile()

# ---- 6. 跑：会自动循环"模型→工具→模型→…"直到模型不再要工具 ----
result = app.invoke({"messages": [("user", "我的笔记里讲链表的那篇说了什么？")]})
print(result["messages"][-1].content)
```

对照 01 号那个 15 行 while 循环逐行看：**一模一样的流程，只是循环变成了图上的回边，状态变成了 State 公告板**。能讲清这个对应关系，"为什么用 LangGraph 而不是裸写"就有了答案：复杂多步流程（分支、并行、人工介入、断点恢复）下，图结构的可观测、可暂停（checkpoint）优势才显现；简单场景裸写更清晰——这个判断面试会问（见第 4 节）。

进阶概念（做完项目再看）：
- **checkpoint**：状态持久化（`checkpointer=MemorySaver()` / SqliteSaver），每步存档 → 支持断点恢复、时间旅行调试、"人审后再继续"（Human-in-the-loop，生产 Agent 的标配）
- **并行节点**：多个工具同时调（图里天然就是多条边并发，裸写循环要自己开线程）

### 第 3 层：MCP（Model Context Protocol，1 周）

Agent 接工具的行业标准协议（2026 年 JD 高频词）。

- 理解：📌 给模型提供工具，从"每个应用自己在请求里定义 tools JSON"进化为"**标准化 Server，任何支持 MCP 的客户端即插即用**"。类比：Function Calling 是"点对点供电"，MCP 是"统一插座的电网"——工具写一次，Claude Code/Cursor/你的 Agent 都能用
- 协议角色：**Host**（如 Claude Desktop/Cursor）→ 连接 **Server**（你写的，暴露工具）→ Server 提供_tools/resources/prompts_
- **动手：写一个 MCP Server**（哪怕只暴露一个 `query_blog(keyword)` 工具）——简历直接加分项

```python
# code/05_agent/mcp_kb_server.py    pip install "mcp[cli]"
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("kb")                       # ← Server 名字（客户端列表里显示用）

@mcp.tool()                               # ← 和 LangChain 的 @tool 长得像，但走的是MCP协议
def query_kb(keyword: str) -> str:
    """在个人知识库（markdown 笔记）里按关键词查询，返回匹配文章的标题和摘要列表"""
    # ↑ docstring 同样是给模型看的说明书（三个框架一个道理：说明书=一切）
    # 真实实现：遍历 03_rag/data/*.md 匹配关键词，或调 03 号建好的 FAISS 索引
    arts = [{"title": "03-单链表", "summary": "单链表结构与插入删除…"}]
    return json.dumps([a for a in arts if keyword in a["title"]], ensure_ascii=False)

if __name__ == "__main__":
    mcp.run(transport="stdio")            # ← stdio：宿主进程用标准输入输出和Server通信
```

接入 Cursor / Claude Desktop 的配置（它们都是 MCP Host）：

```json
// ~/.cursor/mcp.json（Cursor）或 claude_desktop_config.json（Claude Desktop）
{
  "mcpServers": {
    "kb": {
      "command": "python",
      "args": ["/绝对路径/code/05_agent/mcp_kb_server.py"]
    }
  }
}
```

配好后重启客户端，对话框里就能"搜我知识库里关于 X 的笔记"——你的知识库变成了 AI 工具生态的一部分。验收：宿主成功调用并返回结果。

### 第 4 层：Multi-Agent 与评测（2 周，面试深挖区）

三种经典协作模式（按需选，别为了炫技上多 Agent）：

```
① 路由模式（Supervisor）：一个主管模型判断任务类型，分派给专职 Agent
   用户问题 → [主管] ──技术问题──→ [检索Agent] ─┐
                └────闲聊────→ [直接回答]      ├→ 汇总给用户
   适用：任务类型多，单个 Agent 的工具表太长导致选择变笨时

② 流水线模式（Pipeline）：接力棒
   [检索Agent] → [写作Agent] → [审校Agent]
   适用：任务天然分阶段，各阶段技能不同

③ 辩论/校验模式（Critic）：一个产出，另一个挑刺，循环收敛
   [回答Agent] ⇄ [批评Agent]（"这个引用是编的吗？"）→ 满意才输出
   适用：对幻觉敏感的高要求场景
```

⚠️ 多 Agent 的代价：token 消耗成倍涨、延迟变长、链路越长越难调试。**能单 Agent 解决就别多 Agent**——这句话本身就是面试加分点。

**评测（Evals）**：延续 03 的 hit@5 思路，这是区分"玩过 demo"和"能落地"的分水岭：

| 指标 | 定义 | 数据来源 |
|---|---|---|
| 任务成功率 | 完整达成用户多步任务的比例 | 20 个多步任务，人工判最终状态（如"草稿真的建了吗"） |
| 工具调用准确率 | 选对工具且参数正确的比例 | 记录每次 tool_call，人工/自动比对 |
| 平均步数 | 完成任务用了几轮工具调用 | 越少越省 token（链路日志直接统计） |
| 死循环率 | 达到循环上限未完成的占比 | 越低越好，防死循环设计的直接量度 |

评测集示例（20 条，形如）：

```json
[
  {"task": "查知识库里讲链表的笔记，总结成一段话存成草稿《链表笔记汇总.md》",
   "check": "drafts/ 目录新增该文件 且 内容确实来自链表笔记"},
  {"task": "知识库里一共几篇笔记？最近修改的是哪篇？",
   "check": "回答的数量与 data/ 目录一致 且 文件名正确"}
]
```

### 第 5 层：进阶加分（学有余力）

- 跑通一次 SFT/LoRA 微调（LLaMA-Factory + 开源小模型，云算力即可）
- 给开源 Agent 框架提 PR（深信服 JD 原文："参与过开源 Agent 框架开发者优先"）

## 2. 实践项目：知识库问答 → 知识库 Agent（code/05_agent/）

把 03 的问答项目升级成能**连续调用多个工具**的智能体：

```
用户："帮我看看知识库里有没有讲链表的笔记，有的话总结成一段简介，
       存成草稿文件《链表笔记汇总.md》"

Agent 执行链（LangGraph 编排）：
  检索知识库(RAG工具) → 读原文件(读文件工具) → 总结(模型节点)
  → 写入草稿(写文件工具) → 汇报结果
```

- 工具集：`search_kb`（RAG，复用 03 的 FAISS）、`read_note`（读 03_rag/data/ 原文）、`create_draft`（往 drafts/ 写 markdown）
- 路由节点：模型判断直接回答还是调工具（就是 §1 第 2 层代码里的 `should_continue`）
- 防死循环：循环上限（LangGraph 用 `recursion_limit`，裸写用 `for _ in range(10)`）+ 工具执行 try/except，**报错信息以 role=tool 回喂**让模型自己换路
- 评测：按 §1 第 4 层构造 20 个多步任务，统计任务完成率

**AI 规矩不变**：LangGraph 的图结构自己搭，AI 只许讲概念。

## 3. 验收标准

- [ ] LangGraph 项目跑通：连续 3+ 次工具调用的多步任务成功率 ≥ 70%
- [ ] 自写 1 个 MCP Server 并被宿主（Cursor/Claude）成功调用
- [ ] 能白板画出 Agent 的状态图并解释每个节点（含循环边和条件边）
- [ ] README：架构图 + 评测表 + 与 03 版（纯 RAG）的能力对比
- [ ] 自测：不看笔记说出"01 号 15 行循环"与 LangGraph 图的逐项对应关系

## 4. 面试常见问法（附答题骨架）

1. **LangChain/LangGraph 各解决什么问题？什么时候不用框架？**
   → LangChain 统一模型/模板/工具的封装；LangGraph 把多步 Agent 流程建模成图，天然支持分支、循环、checkpoint。逻辑简单（一问一答+一次工具调用）时裸写 01 号那个循环更清晰、更好调试；流程复杂、要断点恢复/人工介入时上图。
2. **你的 Agent 怎么防止死循环/工具调用失败？**
   → 循环上限（recursion_limit）；工具执行包 try/except，**把报错文本作为 tool 结果回喂**，模型会自己换方案；关键写操作（建草稿）加确认节点。
3. **怎么评测一个 Agent 的好坏？**
   → 不要说"跑起来看感觉"。答：预先构造任务集（20 条多步任务+可校验的最终状态），统计任务成功率/工具调用准确率/平均步数/死循环率，改动前后对比出数字（和 03 的 hit@5 一个思想）。
4. **MCP 和 Function Calling 什么关系？**
   → FC 是模型侧协议（模型怎么表达"我要调工具"）；MCP 是应用侧生态（工具怎么被标准化地提供给任何 Host）。MCP Server 暴露的工具，最终仍以 FC 形式被模型调用。

---

## 5. 配套视频（B站，辅助用）

> 用法：19分钟原理片先看 → 尚硅谷大课对应"第 2 层 LangGraph"系统学；黑马课（03 里那条）的 Agent 章节对应第 1、4 层。

| 用途 | 视频 | 说明 |
|---|---|---|
| 先看：LangGraph 快速入门与原理（19分钟） | https://www.bilibili.com/video/BV1HVFLzfEeS | 4.5万播放，状态机/图模型的核心思想，配合作出"要不要上框架"的判断 |
| 尚硅谷 LangGraph 系统课（主教程，21小时） | https://www.bilibili.com/video/BV1z3NY66EY1 | 尚硅谷官方，65万播放，入门+智能体项目实战，对应本笔记第 2-4 层，按需挑章节 |
| 3小时浓缩版（备选） | https://www.bilibili.com/video/BV1PaWgz1Eu6 | AIDeepCoder，基础+进阶，时间紧时替代上面大课 |
