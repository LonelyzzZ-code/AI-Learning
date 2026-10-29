from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.runnables.base import RunnableSerializable
import os

client = ChatZhipuAI(
    model = "glm-4-flash",
    api_key = os.environ["ZHIPU_API_KEY"]
)

chat_template = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个边塞诗人，可以作诗。"),
        MessagesPlaceholder("history"),
        ("human", "请再来一首")
    ]
)
history_data = [
    ("human", "你来写一个唐诗"),
    ("ai", "床前明月光，疑是地上霜，举头望明月，低头思故乡")
]

chain: RunnableSerializable = chat_template | client
resp = chain.stream({"history": history_data})
for chunk in resp:
    if chunk:
        print(chunk.content, end = "", flush = True)