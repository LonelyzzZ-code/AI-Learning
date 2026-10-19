# AI 基础学习练习代码

「基地 AI 知识学习与进阶」学习仓库：主线笔记在 `File/`（00 总览 → 01 LLM API → 02 Prompt → 03 RAG → 04 AI 编码工具 → 05 Agent → 06 Java 后端），实验记录在 `notes/`，练习代码在 `code/`。

## 内容

| 目录 | 说明 |
| --- | --- |
| `code/LLM-API/` | 01号：多轮对话小脚本（text1.py，验证模型无状态） |
| `code/function_calling/` | 01号：Function Calling 四步完整示例 + 请求/响应 JSON 样例 |
| `code/SSE/` | 01号综合：FastAPI + 智谱 GLM 的 SSE 流式服务（LLM-api.py + index.html 测试页） |
| `code/prompt_project/` | 02号：Prompt 练习（few-shot 改写器 / 自动打标签 / 温度对照），prompts.py 为全部提示词收口 |
| `notes/` | 各模块实验记录与踩坑实录（按模块分文件夹） |

## 运行（以 SSE 服务为例）

```bash
# 1. 设置 API Key 环境变量
export ZHIPU_API_KEY="你的key"

# 2. 安装依赖
pip install fastapi uvicorn openai

# 3. 启动服务（LLM-api.py 会自动把 code/prompt_project/ 加进模块路径，引用 prompts.py）
cd code/SSE
uvicorn LLM-api:app --reload
```

接口：`POST /api/ai/chat`，入参 `{"question": "..."}`，返回 SSE 流式响应。浏览器打开 <http://127.0.0.1:8000/index.html> 即测试页。
