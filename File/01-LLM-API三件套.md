# 01 · LLM API 三件套：对话 / 流式 / Function Calling

> 目标：跑通三个能力 + 在 code/SSE/ 独立写出 `POST /api/ai/chat`（SSE 流式）小服务
> 耗时预估：1-2 周（每天 1-1.5h）
> 📌 本模块是全套的地基：03 RAG 的生成环节、05 LangGraph 的"图"、06 Spring AI 的 ChatClient，底下全是这三件事。

---

## 0. 原理背景：什么是"调 API"

**大模型不在你的电脑上，而在厂商机房里。** 训练和运行需要成百上千张显卡，个人电脑带不动。所以厂商把它部署在云端，开放一个"接口"（API）：

> 📌 **大模型 API = 一个放在别人服务器上的远程函数**：你发一段文字（HTTP 请求）过去，它回一段文字（HTTP 响应）回来。

类比点外卖：你（程序）下单（HTTP 请求）→ 商家做菜（模型生成）→ 送达（HTTP 响应）。

### 0.1 先懂两个词：API Key 和 Token

**API Key（密钥）**：一串类似 `a1b2c3d4....x86f` 的字符，相当于你的"会员卡号"。每次请求带上它，厂商才知道找谁计费/限流。⚠️ 它等于钱，只能放环境变量，永远不能写进代码或提交到 GitHub（配置方法见 00 号第四节）。

**Token（词元）**：模型处理文本的最小单位，也是**计费单位**和**长度限制单位**。

```
数值算例（建立体感）：
"我写过关于Redis缓存的文章吗"  ≈ 12 个字 ≈ 10~12 个 token（中文大致 1 字 ≈ 1 token）
英文 "hello world"            = 2 个 token（hel·lo 之类按子词切分，约 4 字符/token）

一次典型对话的账单（glm-4-flash 免费，按 DeepSeek 价目估算数量级）：
  输入 1000 token + 输出 500 token ≈ ¥0.003
结论：单次对话几乎不要钱，但 Prompt 里塞整本书（10 万 token）就又贵又慢。
```

📌 **上下文窗口（Context Window）**：一次请求能装下的最大 token 数（历史+资料+问题全算）。glm-4-flash 是 128K。超了就报错或被截断——这就是为什么后面 RAG 要"切块"、多轮对话要"截断历史"。

### 0.2 准备（一次性）

1. 注册 open.bigmodel.cn，创建 API Key（`glm-4-flash` 模型免费）
2. `pip install openai`（智谱接口兼容 OpenAI 的库，用法完全一样——这是行业惯例：**OpenAI 的接口格式是事实标准**，国内外模型厂商基本都兼容它）

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["ZHIPU_API_KEY"],                  # ← 会员卡号，从环境变量读
    base_url="https://open.bigmodel.cn/api/paas/v4/"      # ← 换成智谱的"门店地址"；不写默认OpenAI
)
```

`client` 就是"外卖电话"，三件事都用它打。

---

## 1. 第一件：对话调用

### 数据长什么样

请求（你发出去的）：

```json
{
  "model": "glm-4-flash",
  "messages": [
    { "role": "user", "content": "用一句话解释什么是RAG" }
  ]
}
```

响应（模型回的）：

```json
{
  "choices": [
    { "message": { "role": "assistant", "content": "RAG是检索增强生成，……" } }
  ]
}
```

### role 规则（多轮对话的原理）

📌 **模型无记忆**：服务端不保存你的对话。每次请求都是独立的一锤子买卖，模型只看你这次发的完整 `messages` 数组。所以"多轮对话" = 每次都把历史一起重发：

| role          | 含义                           | 谁写的               |
| ------------- | ------------------------------ | -------------------- |
| `system`    | 给模型的人设/规则，放最开头    | 你（开发者）         |
| `user`      | 用户说的话                     | 用户                 |
| `assistant` | 模型之前说的话                 | 模型（你存下来重发） |
| `tool`      | 工具执行的结果（第三件套用到） | 你的代码             |

**数值算例：两轮对话，messages 数组怎么变**

```
第 1 轮用户问"什么是RAG"，你发：
messages = [
  {"role":"user","content":"什么是RAG"}
]
模型回："RAG是检索增强生成……" ← 你必须自己存下来

第 2 轮用户问"它能解决什么问题"，你发的是三条：
messages = [
  {"role":"user","content":"什么是RAG"},                        ← 第1轮的问题
  {"role":"assistant","content":"RAG是检索增强生成……"},          ← 第1轮模型的回答
  {"role":"user","content":"它能解决什么问题"}                    ← 新问题
]
模型"想起来"上文，是因为你把上文原样重发了，不是它记得。
```

⚠️ 由此推论：对话越长，每次发的 token 越多、越贵、越慢。生产代码要**截断历史**（如只保留最近 10 轮）。这个坑在 01 综合任务里就会遇到。

### 代码（第一发）

```python
resp = client.chat.completions.create(      # ← 调"对话补全"这个远程函数
    model="glm-4-flash",                    # ← 用哪个模型（免费款）
    messages=[{"role": "user", "content": "用一句话解释什么是RAG"}],
)
print(resp.choices[0].message.content)
# 取值链条：resp(整个响应) → .choices[0](第1个候选) → .message(消息体) → .content(文字正文)
# 为什么有 choices[0]：API 设计上可返回多个候选，实际永远取第 0 个即可
```

---

## 2. 第二件：流式输出（stream / SSE）

### 解决什么问题

模型是一个字一个字往外生成的。回复 500 字要 10 秒：

- 非流式：全生成完才返回 → 用户盯白屏 10 秒
- 流式：每生成一小段立刻发一段 → 打字机效果（ChatGPT 的样子）

类比：非流式 = 等水桶装满再端给你；流式 = 水管直接对着你流。

📌 **SSE（Server-Sent Events）**：实现"服务器一块一块推"的 HTTP 标准格式，消息以 `data: ` 开头、`\n\n` 结尾。**JD 高频词**，前后端各有一套写法，本节两端都给全。

### 数据长什么样

加 `stream=True` 后，`create()` 不再返回一个响应对象，而是返回一个**迭代器**，服务器连续发来很多小块（chunk），每块只有新增的几个字：

```json
{ "choices": [ { "delta": { "content": "深" } } ] }
{ "choices": [ { "delta": { "content": "圳" } } ] }
{ "choices": [ { "delta": {}, "finish_reason": "stop" } ] }
```

`delta` = 增量（这次新增的字）。所有 delta 拼起来才是完整回答。
📌 `finish_reason`：结束原因，`"stop"`=正常说完，`"length"`=被 max_tokens 截断，`"tool_calls"`=模型想调工具（第三件套）。

### 代码（客户端收流）

```python
stream = client.chat.completions.create(
    model="glm-4-flash",
    messages=[{"role": "user", "content": "写一首关于深圳的短诗"}],
    stream=True,                                  # ← 唯一区别：开流
)
full = ""                                         # ← 自己拼接全文
for chunk in stream:                              # ← 一块一块接
    if chunk.choices[0].delta.content:            # ← 有些块 delta 是空的(元信息)，跳过
        piece = chunk.choices[0].delta.content
        print(piece, end="", flush=True)          # ← flush=True 立刻上屏，才看得到打字机
        full += piece
print(f"\n[完整回答共{len(full)}字]")
```

⚠️ 注意取值从 `choices[0].message.content` 变成了 `choices[0].delta.content`——流式里没有 `message`，只有 `delta`。面试爱问这个区别。

### 服务端转发（FastAPI + SSE，本模块综合任务的完整版）

模型流式给你的服务器，你的服务器再流式给浏览器——**两段流要接起来**。成品在 `code/SSE/` 文件夹（LLM-api.py + index.html），独立单文件服务：

```python
# code/SSE/LLM-api.py —— 独立小服务，一个文件搞定
import os
import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel          # ← 入参校验（fastapi 自带 pydantic）
from openai import OpenAI

app = FastAPI()
client = OpenAI(
    api_key=os.environ["ZHIPU_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

class ChatIn(BaseModel):                # ← 用 Pydantic 模型收参，而不是裸 dict（有校验、有文档）
    question: str

@app.post("/api/ai/chat")
def ai_chat(data: ChatIn):
    def gen():                                          # ← 生成器：被 StreamingResponse 按需拉取
        stream = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": data.question}],
            stream=True,
        )
        for chunk in stream:
            piece = chunk.choices[0].delta.content
            if piece:
                # SSE 格式铁律：每条消息以 "data: " 开头、"\n\n" 结尾（两个换行缺一不可）
                yield f"data: {json.dumps({'text': piece}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"                        # ← 自定义结束标记，前端据此停止

    return StreamingResponse(gen(), media_type="text/event-stream")  # ← SSE 的 MIME 类型
```

在 LLM-api.py 末尾再挂一行静态目录（顺便把下面的测试页服务出去）：

```python
app.mount("/", StaticFiles(directory=".", html=True), name="static")
# ← 把当前目录挂成静态站：浏览器开 http://127.0.0.1:8000/index.html 就是测试页
```

跑起来（在 code/SSE/ 目录下，先 `pip install fastapi uvicorn`）：

```bash
uvicorn LLM-api:app --reload   # ← 跑 LLM-api.py 里的 app 对象；--reload 改代码自动重启
                              #    模块名带连字符 importlib 也能加载，但别用 import 语句引它
```

逐行要点：

- `gen()` 是**生成器函数**（有 yield）：StreamingResponse 每次向客户端写一块，才向 gen 要下一块——这就是"接力水管"，不是先攒齐再发
- `media_type="text/event-stream"`：告诉浏览器"这是 SSE 流"，Content-Type 错了前端收不到事件
- `[DONE]` 是约定俗成的结束哨（OpenAI 官方流也这么干）

### 前端读取（测试页 index.html + fetch）

⚠️ 浏览器自带的 `EventSource` **只支持 GET**，我们接口是 POST，所以用 `fetch` + `ReadableStream` 手动读。测试页是 `code/SSE/index.html`（一个输入框 + 一个按钮 + 一个显示区的最简页面），核心 JS：

```javascript
// 点击"发送"按钮后调用。index.html 与接口同源（都由 LLM-api.py 服务），fetch 直接写相对路径
async function askAI(question) {
  const resp = await fetch('/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question })
  })
  const reader = resp.body.getReader()      // ← 把响应体变成"流读取器"
  const decoder = new TextDecoder()         // ← 字节流 → 中文字符串
  let buf = '', answer = ''
  while (true) {
    const { done, value } = await reader.read()   // ← 每次读"到现在为止到达的一块"
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const events = buf.split('\n\n')       // ← SSE 以 \n\n 分隔事件
    buf = events.pop()                     // ← ⚠️ 最后一段可能被网络截半，留到下轮再拼
    for (const e of events) {
      const data = e.replace(/^data: /, '') // ← 剥掉 "data: " 前缀
      if (data === '[DONE]') return answer
      answer += JSON.parse(data).text       // ← 更新到页面上就有打字机效果
    }
  }
}
```

⚠️ 前端最常见的 bug：忘了 `buf = events.pop()`，网络把一条消息劈成两半时 JSON.parse 报错。SSE 解析必须按 `\n\n` 切并保留不完整的尾巴。

---

## 3. 第三件：Function Calling（Agent 的心脏）

### 解决什么问题

模型只知道训练数据里的东西，不能查天气、查数据库、读文件。

### 核心思想

> 📌 **模型不能干活，但它判断力最强 → 让它当指挥，你的代码当手。**

协议四步：

```
① 你声明工具（名字+说明书+参数格式）
        ↓
② 模型返回"调用请求"：我要调 get_weather，参数 {"city":"深圳"}
        ↓
③ 你的代码真的执行这个函数（查库/调API/读文件……）
        ↓
④ 执行结果以 role="tool" 发回，模型生成最终回答
```

### ⚠️ 最易误解的点

**模型从头到尾没有执行任何东西。** 它只输出了一段结构化文字（"我想调某函数"）。真正执行的是你的 Python 代码。它是指挥官，不是士兵。面试问"Function Calling 的原理"，这句话就是标准答案的第一句。

### 逐步数据算例

**第 1 步 · 你的请求（带工具声明）：**

```json
{
  "model": "glm-4-flash",
  "messages": [{ "role": "user", "content": "深圳今天天气怎么样？" }],
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "查询指定城市的实时天气",
      "parameters": {
        "type": "object",
        "properties": { "city": { "type": "string" } },
        "required": ["city"]
      }
    }
  }]
}
```

📌 `description` 是写给**模型**看的说明书，模型靠它判断"何时用这个工具、怎么填参数"。写得越准，调用越对——它和 System Prompt 一样是 Prompt 工程（02 号）的对象。
`parameters` 那坨叫 **JSON Schema**：描述参数名、类型、哪些必填。模型照着它填参数。

**第 2 步 · 模型响应（不是文字回答，是调用请求）：**

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,                        ← 注意：正文是空的！
      "tool_calls": [{
        "id": "call_001",                     ← 这次调用的编号（回传结果要对号）
        "function": { "name": "get_weather",
                      "arguments": "{\"city\": \"深圳\"}" }
      }]
    },
    "finish_reason": "tool_calls"             ← 结束原因=想调工具
  }]
}
```

⚠️ `arguments` 是**字符串形式**的 JSON（不是 JSON 对象），代码里必须 `json.loads()` 解析。忘解析直接当 dict 用会报 TypeError。

**第 3 步 · 你的代码执行：**

```python
args = json.loads(call.function.arguments)   # {'city': '深圳'}  ← 字符串→dict
result = {"city": "深圳", "temp": "30℃"}      # 真实项目里去查API/数据库
```

**第 4 步 · 结果回传（messages 里已有 3 条 + 新增 1 条）：**

```python
final = client.chat.completions.create(
    model="glm-4-flash",
    messages=[
        {"role": "user", "content": "深圳今天天气怎么样？"},   # ① 最初问题
        msg,                                                    # ② 模型的调用请求(原样带回)
        {"role": "tool", "tool_call_id": call.id,               # ③ 对应哪次调用
         "content": "{\"city\": \"深圳\", \"temp\": \"30℃\"}"}, # ④ 执行结果(字符串)
    ],
)
print(final.choices[0].message.content)   # "深圳今天30℃……"
```

⚠️ `msg`（模型的调用请求）必须原样放回 messages，缺了它模型不知道"这是哪次调用的结果"，会报 400。
`tool_call_id` 用来在**多工具调用**时对号入座（模型一次可能要调 2 个工具，返回 2 个结果，靠 id 配对）。

### 完整可跑代码（从这开始可直接抄进 py 文件运行）

```python
import json
from openai import OpenAI

client = OpenAI(api_key=os.environ["ZHIPU_API_KEY"],
                base_url="https://open.bigmodel.cn/api/paas/v4/")

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的实时天气",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}]

resp = client.chat.completions.create(                       # ① 带工具问模型
    model="glm-4-flash",
    messages=[{"role": "user", "content": "深圳今天天气怎么样？"}],
    tools=tools,
)
msg = resp.choices[0].message

if msg.tool_calls:                                           # ② 模型要调工具吗
    call = msg.tool_calls[0]
    args = json.loads(call.function.arguments)               # ③ 解析参数，真的执行
    result = {"city": args["city"], "temp": "30℃", "cond": "晴"}

    final = client.chat.completions.create(                  # ④ 结果回喂，拿最终回答
        model="glm-4-flash",
        messages=[
            {"role": "user", "content": "深圳今天天气怎么样？"},
            msg,                                             # ← 调用请求原样带回
            {"role": "tool", "tool_call_id": call.id,
             "content": json.dumps(result, ensure_ascii=False)},
        ],
    )
    print(final.choices[0].message.content)
```

### 终极推论：Agent = Function Calling 放进循环

只调一次工具，能干的事有限。把四步**套进 while 循环**，模型就能"调工具→看结果→再决策→再调工具"，这就是 📌 **Agent（智能体）** 的全部本质：

```python
tools = [...]                                        # 声明全部工具
messages = [{"role": "user", "content": "帮我查知识库里关于链表的笔记并总结"}]

for _ in range(10):                                  # ← 循环上限=防死循环（面试点）
    resp = client.chat.completions.create(model="glm-4-flash",
                                          messages=messages, tools=tools)
    msg = resp.choices[0].message
    messages.append(msg)                             # ← 每步都追加进历史
    if not msg.tool_calls:                           # ← 模型不再要工具 = 最终回答
        print(msg.content); break
    for call in msg.tool_calls:                      # ← 可能一次要多个工具
        result = run_tool(call.function.name,
                          json.loads(call.function.arguments))  # ← 你的执行器
        messages.append({"role": "tool", "tool_call_id": call.id,
                         "content": json.dumps(result, ensure_ascii=False)})
```

这段 15 行的循环请**逐行背下来**——05 号的 LangGraph 只是把这张循环画成了图，06 号的 Spring AI Tool Calling 只是把这套协议换成了 Java 注解。框架会过时，这个循环不会。

---

## 4. 三件套 → 产品的对应关系

| 产品                | 用到的                                                                                                |
| ------------------- | ----------------------------------------------------------------------------------------------------- |
| 普通聊天网页        | ① + ②                                                                                               |
| ChatGPT 联网/查天气 | ① + ② + ③                                                                                          |
| **Agent**     | ③ 放进**循环**（可连续调多个工具、看结果、再决策）。RAG/LangChain/LangGraph 全建立在这个循环上 |

---

## 5. 常见报错速查（跑不通先看这张表）

| 报错/现象                    | 原因                                      | 解法                                                                    |
| ---------------------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| 401 AuthenticationError      | Key 错 / 没读到环境变量                   | `echo $ZHIPU_API_KEY` 检查；改完 `.zshrc` 要 `source`，IDE 要重启 |
| 404 model not found          | 模型名拼错                                | 严格写`glm-4-flash`，全小写                                           |
| 429 rate limit               | 调太频繁                                  | `time.sleep(1)` 或加重试                                              |
| 连接超时                     | base_url 拼错 / 断网                      | 检查末尾有`/`：`.../api/paas/v4/`                                   |
| TypeError: string indices    | FC 里忘了`json.loads(arguments)`        | 见 §3 第 3 步                                                          |
| 400 tool message must be ... | 回传结果时没带`msg` 或 `tool_call_id` | messages 三件套：问题+请求+结果，id 对号                                |
| 前端 JSON.parse 报错         | SSE 消息被网络截半                        | 按本文 §2 前端代码处理`events.pop()`                                 |
| 打字机不生效                 | print 没 flush / 前端没逐块渲染           | `flush=True`；Vue 里用响应式变量累加                                  |

---

## 6. 自测题（不看笔记作答，再翻回去核对）

1. 模型 API 是无状态的，那 ChatGPT 怎么"记住"你上一句话？
2. `stream=True` 之后，响应对象的取值链条有什么变化？`delta` 和 `message` 的关系？
3. Function Calling 全流程中，模型做了什么、你的代码做了什么？（各两句话）
4. `tool_call_id` 解决什么问题？
5. SSE 消息的格式是什么？为什么前端解析要按 `\n\n` 切、还要 `pop()` 尾巴？
6. Agent 的本质用一句话+一段伪代码说出来。

<details>
<summary>参考答案（先自己答再看）</summary>

1. 客户端/后端把历史 messages 每次全量重发；模型本身什么都不记得。
2. 返回值从响应对象变成迭代器；`choices[0].message.content` → `choices[0].delta.content`；所有 delta 拼接 = message.content。
3. 模型：判断需要哪个工具、产出结构化调用请求（name+arguments JSON），收到结果后生成自然语言回答。代码：声明工具、解析 arguments、真正执行函数、把结果以 role=tool 回传。
4. 一次回复可能含多个 tool_call，回传多个结果时靠 id 配对，避免张冠李戴。
5. `data: 内容\n\n`；一条消息可能被网络分包截断，半条消息不能解析，留到下一块到达再拼。
6. "Function Calling 放进循环"；伪代码见 §3 末尾 15 行。

</details>

---

## 7. 实践任务（在本子上打勾）

- [X] 注册智谱，拿到 API Key，配好环境变量，跑通 ① 基础对话（10 分钟）
- [X] 跑通 ② 流式，亲眼看打字机效果（10 分钟）
- [X] 跑通 ③ Function Calling 完整 4 步（半天，重点逐行理解）
- [X] 手写"多轮对话"小脚本：循环里维护 messages 数组，连续问 3 轮，验证模型记得上文；然后故意只发最新一条，看它失忆（20 分钟，理解"无状态"）
- [X] **综合任务：在 code/SSE/ 独立写出 `POST /api/ai/chat` 小服务**（完整代码见 §2 服务端+前端两段，先自己敲，卡 30 分钟再看）
  - code/SSE/：LLM-api.py（含静态挂载）+ index.html
  - `uvicorn LLM-api:app --reload` 跑起来，浏览器开 http://127.0.0.1:8000/index.html 看打字机效果
  - 进阶：把最近 5 轮历史带进 messages（模拟真实聊天）
- [X] 面试自测：不看笔记向同学讲清"Function Calling 里模型做了什么、你的代码做了什么"

**验收标准**：浏览器测试页能打字机式显示 AI 回复，且能连续对话不失忆 → 本模块通关。

---

## 8. 配套视频（B站，辅助用）

> 用法：本笔记是主线任务清单，视频只用来补背景原理。**看完 ≠ 会，跑通笔记里的任务才算**。倍速看、跟着敲。

| 用途                            | 视频                                        | 说明                                                               |
| ------------------------------- | ------------------------------------------- | ------------------------------------------------------------------ |
| 先看：智谱平台上手（9分钟）     | https://www.bilibili.com/video/BV1Agt1zHE8e | 免费注册、拿 Key、第一发调用，快速建立体感                         |
| API Key 获取与本地调用实操      | https://www.bilibili.com/video/BV1ja4y1y7Aj | 九天Hector，33分钟，照着做一遍                                     |
| Function Calling 原理（重点）   | https://www.bilibili.com/video/BV1qTYizcEN3 | 10.6万播放，讲透 FC 与 MCP 协议为何这样设计——配合本文第 3 节食用 |
| Function Calling 系统课（13集） | https://www.bilibili.com/video/BV1SJm8YtETd | 理论到实战，卡壳时按需挑集看                                       |
