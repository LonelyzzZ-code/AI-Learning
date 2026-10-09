import os
import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel          # ← 入参校验（fastapi 自带 pydantic）
from openai import OpenAI

app = FastAPI()
client = OpenAI(
    api_key = os.environ["ZHIPU_API_KEY"],
    base_url = "https://open.bigmodel.cn/api/paas/v4/"
)

class ChatIn(BaseModel):
    question: str

@app.post("/api/ai/chat")
def ai_chat(data: ChatIn):
    def gen(): #生成器:被StreamingResponse按需拉取
        stream = client.chat.completions.create(
            model = "glm-4-flash",
            messages = [{"role": "user","content": data.question}],
            stream = True,
        )
        for chunk in stream:
            piece = chunk.choices[0].delta.content
            if piece:
                # SSE 格式规则：每条消息以 "data: " 开头、"\n\n" 结尾（两个换行缺一不可）
                yield f"data:{json.dumps({'text': piece},ensure_ascii=False)}\n\n"
                #顺序：把文本转换成字典 -> 把字典转换成JSON格式 -> 套上SSE的外壳进行输出
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(),media_type = "text/event-stream")

app.mount("/", StaticFiles(directory = ".", html = True),name = "static")
#把当前目录挂成静态网址
