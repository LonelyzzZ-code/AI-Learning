# 06 · Java AI 后端进阶（分叉方向 B）

> 前置：校内 Java 课程 + 基地 01-04（Spring AI 底下就是那套 messages/tools 协议）
> 时间：寒假启动，大二下并行推进
> 目标岗位依据：艾氪智能 Java 后端开发（AI平台和AI智能体）JD（20-40k，深圳南山）
> 💡 学习心法：这一层没有全新知识——JVM/并发是 Java 面试三件套，Spring 生态对应你已做过的 FastAPI 概念，Spring AI 对应 01 号三件套。**每个知识点先找"我在 Python 里做过的对应物"，迁移着学。**

---

## 1. 知识树（按顺序）

### 第 1 层：Java 核心（JVM + 并发，面试三件套）

#### 1.1 JVM 内存结构（先背图，再逐区理解）

```
JVM 运行时数据区
├─ 线程私有（每个线程一份，随线程生灭）
│   ├─ 程序计数器：记录当前线程执行到哪条字节码
│   ├─ 虚拟机栈：每调一个方法压一个"栈帧"（局部变量表+操作数栈），方法返回就弹出
│   │            ← StackOverflowError 就是栈帧压太深（如无限递归）
│   └─ 本地方法栈：同上，服务 native 方法
└─ 线程共享
    ├─ 堆（Heap）：对象都住这，GC 的主战场
    │   ├─ 新生代 Young：Eden + S0 + S1
    │   └─ 老年代 Old
    └─ 方法区（JDK8+ = 元空间 Metaspace）：类信息、常量池
```

📌 **分代 GC 的运转逻辑**（数值算例）：

```
new Article() → 对象出生在 Eden
Eden 满了 → 触发 Minor GC（只扫新生代，快）：
  活下来的对象 → 复制到 Survivor 区，年龄+1
  每熬过一次 Minor GC 年龄+1，默认到 15 岁（MaxTenuringThreshold）→ 晋升老年代
老年代也满了 → 触发 Full GC（全堆扫描，慢，会造成"stop the world"停顿）

工程直觉：短命对象（临时 DTO、局部变量装箱）在新生代就被回收，成本极低；
        长命对象（缓存、连接池）挤进老年代，Full GC 频繁 = 接口周期性卡顿。
面试高频：大对象直接进老年代（-XX:PretenureSizeThreshold）为什么？→ 避免在 Eden/S0/S1 间来回复制。
```

学习方式：《JavaGuide》+ 面试题驱动，遇到不懂的写小 demo 验证（如故意无限递归看 StackOverflowError）。

#### 1.2 线程池（JD"精通并发"的第一考点）

📌 **ThreadPoolExecutor 七参数**，逐个注释：

```java
ThreadPoolExecutor pool = new ThreadPoolExecutor(
    2,                                        // ① corePoolSize：常驻核心线程数（来了任务优先它们干）
    4,                                        // ② maximumPoolSize：线程数上限（队列满了才扩到这）
    60, TimeUnit.SECONDS,                     // ③④ 临时线程（超出核心数的）空闲多久后销毁
    new ArrayBlockingQueue<>(100),            // ⑤ 任务队列：⚠️必须用有界队列，无界=OOM隐患
    Executors.defaultThreadFactory(),         // ⑥ 线程工厂（名字、优先级，一般默认）
    new ThreadPoolExecutor.CallerRunsPolicy() // ⑦ 拒绝策略：队列满+线程满时怎么办
);
```

📌 **执行顺序（面试必考的数值算例）**：

```
core=2, max=4, queue=100。依次提交 8 个任务：
任务1、2 → 建核心线程直接执行（2个线程满）
任务3~7 → ⚠️ 不是先开新线程！先进队列排队（队列容量100远没满）
队列永远不会满（8-2=6 < 100）→ maximumPoolSize 根本不会触发
记忆点：核心线程 → 队列 → 扩线程 → 拒绝，顺序不能反，"先排队后招人"

拒绝策略四选一：AbortPolicy 抛异常(默认) / CallerRunsPolicy 提交者自己跑(自然降速) /
               DiscardPolicy 静默丢弃 / DiscardOldestPolicy 丢最老的
```

#### 1.3 并发三板斧（概念+demo 即可，深水区大二下再潜）

- **synchronized / ReentrantLock**：互斥锁，同一时刻只允许一个线程进临界区（Lock 更灵活：可中断、可超时、多条件变量）
- **volatile**：保证**可见性**（一个线程改了，别的线程立刻看到）+ 禁止指令重排；⚠️ **不保证原子性**——`count++` 是"读-加-写"三步，volatile 挡不住交错，要用 `AtomicInteger.incrementAndGet()`
- **JUC 并发容器**：`ConcurrentHashMap`（分段/CAS 并发写）、`CopyOnWriteArrayList`（读多写少场景）

#### 1.4 虚拟线程（JDK 21，简历亮点）

传统线程 1:1 映射内核线程（MB 级栈，几千个就顶天）；虚拟线程由 JVM 调度、挂在少量载体线程上，**百万级随便开**。AI 应用的特点恰是大量 IO 等待（等模型吐 token）——每个请求一个虚拟线程，代码还是同步写法，吞吐接近 WebFlux：

```java
Thread.startVirtualThread(() -> callLlmApi());   // 开虚拟线程和开普通线程一样简单
```

### 第 2 层：Spring 生态 + 分布式（JD 原文逐条对应）

| JD 要求 | 学什么 | 你在 FastAPI 里的对应物 |
|---|---|---|
| Spring Boot / Spring Cloud 微服务 | Boot 自动装配原理；Cloud 组件概念（注册中心/网关/配置中心，起步用理解即可） | FastAPI 应用工厂 + （无对应，补概念） |
| MySQL：SQL 优化、分库分表 | 索引原理（B+树，正好衔接数据结构课）、explain 看执行计划、ShardingSphere 概念 | 数据库课程写过的 SQL |
| Redis | 缓存穿透/击穿/雪崩、分布式锁 | （Python 版未加缓存，Java 版第一次实践） |
| Kafka / RabbitMQ | 消息队列的核心问题：不丢消息、重复消费、顺序（用一次就知道） | （无对应，补概念） |
| Elasticsearch | 倒排索引原理；和 03 的 BM25 检索直接打通 | FAISS + BM25 那两路 |
| Docker + K8s | Docker 必会（部署自己的项目）；K8s 了解 Pod/Service 概念 | （部署时补） |

Redis 缓存标准三件套代码（Java 版，和你在 FastAPI 写过的同构）：

```java
public ArticleVO getById(Long id) {
    String key = "article:" + id;
    String cached = redis.opsForValue().get(key);          // ① 先查缓存
    if (cached != null) return JSON.parseObject(cached, ArticleVO.class);  // ② 命中，直接返回（不碰库）

    ArticleVO vo = articleMapper.selectById(id);           // ③ 未命中，查库
    if (vo != null)
        redis.opsForValue().set(key, JSON.toJSONString(vo), 30, TimeUnit.MINUTES);  // ④ 回填+过期
    else
        redis.opsForValue().set(key, "{}", 2, TimeUnit.MINUTES);  // ⑤ 空值短缓存=防缓存穿透
    return vo;
}
// 三大事故对照（面试必问）：
// 穿透：查不存在的id，每次都打到库 → ⑤空值缓存/布隆过滤器
// 击穿：某个热key过期瞬间大量请求同时打到库 → 只放一个线程去重建（分布式锁）
// 雪崩：大批key同时过期 → 过期时间加随机抖动
```

### 第 3 层：AI 集成层（Java 岗的溢价部分）

#### 3.1 Spring AI：ChatClient（= 01 号三件套的 Java 版）

```yaml
# application.yml —— 配一次，指向智谱（OpenAI兼容协议）
spring:
  ai:
    openai:
      base-url: https://open.bigmodel.cn/api/paas/v4
      api-key: ${ZHIPU_API_KEY}        # ← 同样走环境变量，不进代码不进git
      chat:
        completions-path: /chat/completions   # ← ⚠️ Spring AI 默认在 base-url 后拼 /v1/chat/completions，
                                              #    直连智谱必须改这条（以届时官方文档为准）
        options:
          model: glm-4-flash
```

```java
// 对话（=01号第①件）
String answer = chatClient.prompt()
        .system("你是我的知识库AI助手，回答控制在200字内")   // ← = system 消息（02号人设）
        .user(question)                                    // ← = user 消息
        .call()                                            // ← 非流式
        .content();

// SSE 流式（=01号第②件，复刻你 FastAPI 那个接口）
@GetMapping(value = "/api/ai/chat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<String> chat(@RequestParam String question) {
    return chatClient.prompt().user(question)
            .stream()          // ← stream() 替代 call()，返回 Flux<String>（响应式流）
            .content();        // ← 每个元素 = 一个增量token
    // Spring 自动按 SSE 格式(data: xxx\n\n)推给浏览器——与01号手写的格式完全一致，
    // 所以 01 号的 index.html 不用改，把地址指到 Java 后端就能用
}
```

📌 **Tool Calling**（=01号第③件）：Spring AI 用 `@Tool` 注解声明工具，注解的 description 同样是给模型看的说明书；模型返回 tool_call 后框架自动回调你的方法、把结果回喂、再拿最终回答——**整个协议就是你在 Python 里手写的那 4 步**。

#### 3.2 工程化专题（面试拉开差距的地方）

**token 计费**（Java 线独有亮点）：按用户/接口统计 token 消耗，做计量+限额：

```java
// 每次调用后从响应元数据取 usage（输入/输出token数），Spring AI 直接给：
ChatResponse resp = chatClient.prompt().user(question).call().chatResponse();
Integer inTok  = resp.getMetadata().getUsage().getPromptTokens();     // 输入token
Integer outTok = resp.getMetadata().getUsage().getCompletionTokens(); // 输出token
// 工程闭环：AOP切面/拦截器统一截获 → 按用户累加落库 → 超过日限额直接返回429
// （表：user_id, api_path, model, in_tokens, out_tokens, created_at）
```

**多模型路由**：按任务类型/成本把请求路由到不同模型：

```
请求 → Router（规则：任务类型+问题长度+用户等级）
         ├─ 简单问题/草稿/分类   → glm-4-flash（免费）      ← 80%流量
         ├─ 复杂推理/正式产出    → glm-4-plus（贵但强）
         └─ 主模型超时/限流      → 降级备用模型（保可用性）
面试讲法：这是一道"成本-质量-可用性"的权衡题，拿 01 号的 token 算例说成本账。
```

其余：流式接口的异常处理、超时、降级；工作流引擎概念（Activiti/Flowable）——理解"Agent 编排也是一种工作流"即可。

## 2. 实践项目：Spring Boot 独立实现「知识库 AI 问答」（Java 版，code/06_java/）

**同一套系统用两种语言各从零写一遍**（Python 版 = code/03_rag）——检验"AI 会 vs 我会"，也是第 5 节双栈叙事的来源。

先看目录对照（左边是你 01/03 号亲手写过的 Python 版），迁移成本立刻降一半：

```
Python 版 (code/03_rag)            Spring Boot 版 (code/06_java)
─────────────                     ─────────────────────
main.py（FastAPI 应用）        →   BlogAiApplication.java（@SpringBootApplication）
（无对应，逻辑写在路由里）     →   service/ArticleService.java          ← 业务层（Java惯例单独拆出）
data/*.md + chunks.json        →   MySQL 存文章 + Article.java + Mapper
AskIn(BaseModel)（Pydantic）   →   dto/AskDTO.java（Java Bean + 校验注解）
（裸 python 脚本 + pip）       →   application.yml 配置 + Maven 依赖管理
```

Controller 长什么样（对照你在 FastAPI 写过的分页接口）：

```java
@RestController
@RequestMapping("/api/articles")
public class ArticleController {

    @Autowired private ArticleService service;      // ← 依赖注入：等价于 FastAPI 的 Depends()

    @GetMapping                                  // ← @app.get("/api/articles")
    public PageResult<ArticleVO> list(
            @RequestParam(defaultValue = "1") int page,     // ← Query参数，= page: int = 1
            @RequestParam(defaultValue = "10") int size) {
        return service.page(page, size);
    }

    @PostMapping                                 // ← @app.post，@RequestBody = Pydantic 入参
    public ArticleVO create(@RequestBody @Valid ArticleDTO dto) {
        return service.create(dto);              // ← @Valid 触发校验，= Pydantic 自动校验
    }
}
```

```
第一阶段（寒假）：Spring Boot 基础
  文章管理 CRUD + 分页（MyBatis-Plus 或 Spring Data JPA）
  + Redis 缓存热点文章           ← 第一次在 Java 里做，对照第 2 层表格补原理

第二阶段（大二下）：加 AI 能力
  Spring AI 实现 /api/ai/chat（SSE 流式）    ← 对齐 01 产出（§3.1 代码直接可用）
  Spring AI + pgvector 复刻知识库问答（RAG）    ← 对齐 03 产出
  加 token 计量 + 多模型路由                  ← Java 线独有亮点
```

部署：Docker 打包，你有阿里云服务器（见 whh_code 里的部署方案笔记），直接部署上去，简历写"容器化部署上线"。

**AI 规矩同样执行**：CRUD 和配置可以 AI 辅助，但并发/事务/流式核心代码自己写。

## 3. 双栈对照总表（面试"两个都会"的底气来源）

| 维度 | Python/FastAPI | Java/Spring Boot |
|---|---|---|
| 定位 | 迭代快、AI 生态最全（LangChain 等首发 Python） | 承载稳态业务、企业生态成熟 |
| 类型 | 动态类型，Pydantic 补校验 | 静态类型，编译期查错 |
| AI 集成 | openai SDK / LangChain / LangGraph | Spring AI / LangChain4j |
| 流式 | StreamingResponse + 生成器 | SseEmitter / Flux |
| 并发 | async/await 事件循环 | 线程池（→ JDK21 虚拟线程） |
| 你做的事 | code/03_rag：从 0 到 1 的 Python 版 | code/06_java：同一系统的 Java 版+工程化加强 |

## 4. 验收标准

- [ ] Spring Boot 版跑通：文章管理 CRUD + Redis 缓存，接口行为与 Python 版（code/03_rag）一致
- [ ] SSE 流式 AI 接口上线，01 号的 index.html 改个地址就能直接调用
- [ ] token 计量：每个接口调用的 token 消耗入库可查
- [ ] 线程池七参数+执行顺序能白板讲（含"先排队后招人"算例）
- [ ] 能回答：FastAPI 和 Spring Boot 实现同一功能，各自的取舍是什么（用第 3 节对照表答）

## 5. 双栈的面试叙事（你的独特卖点）

> "我用 Python/FastAPI 和 Java/Spring Boot 实现过同一套知识库 AI 问答系统，
> 包括 SSE 流式、RAG 检索、Redis 缓存。Python 版迭代快适合 AI 探索，
> Java 版适合承接稳态业务——我清楚两者的工程取舍。"

这段话同时够到 Agent 岗（AI 能力）和 Java 后端岗（工程能力），这就是"同一项目做两遍"策略的兑现场景。

---

## 6. 配套视频（B站，辅助用）

> 用法：Spring Boot 基础跟黑马（你熟悉它的节奏）；Spring AI 部分视频较新、播放量不高，以官方文档为主、视频为辅。

| 用途 | 视频 | 说明 |
|---|---|---|
| Spring Boot 快速入门（6小时） | https://www.bilibili.com/video/BV1Lq4y1J77x | 黑马程序员官方，195万播放，先快速跑起来 |
| Spring Boot 系统大课（34.5小时） | https://www.bilibili.com/video/BV15b4y1a7yG | 黑马程序员，292万播放，零基础到项目实战，对应第 2 层，按需挑章节 |
| Spring AI + Langchain4j + RAG（6小时） | https://www.bilibili.com/video/BV1h8G96vEck | 8.6万播放，覆盖第 3 层 AI 集成的大部分主题 |
| Spring AI 2.0 从零到 MCP（8集浓缩） | https://www.bilibili.com/video/BV1Bp4D6CEYx | 乐哥聊编程，播放量不高但精准对口"Java工程师的AI第一课"，含 MCP 实战 |
