# Function Calling 易错点清单

## 一、json 库四兄弟：选错函数最高发

| 函数 | 方向 | 使用场景 |
|---|---|---|
| `json.dumps(obj)` | Python 对象 → **字符串** | 把执行结果塞进 `content` 发给模型前 |
| `json.loads(s)` | **字符串** → Python 对象 | 解包模型的 `arguments` 时 |
| `json.dump(obj, f)` | 对象 → **文件** | 保存数据到文件 |
| `json.load(f)` | **文件** → 对象 | 读取 tools.json |

**记忆口诀：带 s（string）的跟字符串打交道，不带 s 的跟文件打交道；d 系列是打包出去，l 系列是解开进来。**

中文必须加 `ensure_ascii=False`，否则变 `\u6df1\u5733` 乱码。

## 二、API 字段拼写：几乎全是复数

| 正确 ✓ | 常见错误 ✗ | 出现位置 |
|---|---|---|
| `messages` | `message` | 请求参数 |
| `tools` | `tool` | 请求参数 |
| `tool_calls` | `tool_call` | 响应 / assistant 消息 |
| `arguments` | `argument` | `call.function.arguments` |
| `tool_call_id` | `toolcall_id` | tool 角色消息 |

规律：这些字段在 JSON 里全是**数组**，所以都是复数。
另外注意单词本身拼写：`function` 不是 `funtion`/`funciton`。

## 三、JSON 语法符号

1. **一个文件只能有一个顶层对象**，两个对象并列会报"预期为文件结尾"
2. **最后一个元素后不能有逗号**：`["a", "b",]` ✗
3. **嵌套 JSON 字符串里的双引号要转义**：`"{\"city\": \"深圳\"}"`
4. JSON 里没有注释、不能用单引号、key 必须双引号
5. JSON 的布尔和空值是**小写**：`true` / `false` / `null`（不是 Python 的 `True` / `None`）

## 四、Python 细节

1. `with open(...) as f:` 结束时**自动关闭文件**，不要手动 `f.close`
2. 函数调用**必须带括号**：`f.close` 只是拿到函数本身，`f.close()` 才是执行
3. `open()` 加 `encoding="utf-8"`（文件含中文时必写）
4. 相对路径按**敲命令的目录**算，不按 py 文件位置算。稳妥写法：

```python
json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "function-calling-tools.json")
```

5. `=` 是赋值，`==` 是比较

## 五、数据类型坑

1. `call.function.arguments` 拿到的是**字符串**，必须 `json.loads()` 后才能 `["city"]` 取值
2. `content` 字段**只收字符串**，dict 结果必须 `json.dumps()` 再放进去
3. 拿不准就 `print(type(x))` 看一眼是 str 还是 dict

## 提交前自检 Checklist

- [ ] API 字段拼写：`messages` / `tools` / `arguments` 全是复数
- [ ] json 函数选对：操作字符串带 s，操作文件不带 s
- [ ] 发出去的 `content` 是字符串（dict 先 dumps）
- [ ] 收到的 `arguments` 先 loads 再用
- [ ] `open()` 带了 `encoding="utf-8"`
- [ ] JSON 文件：单顶层对象、无尾逗号、双引号
