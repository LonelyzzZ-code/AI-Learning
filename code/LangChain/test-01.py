import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage,SystemMessage
import os

llm = ChatZhipuAI(
    model = "glm-4-flash",
    api_key = os.environ["ZHIPU_API_KEY"],
)
messages = [
    SystemMessage(content = "你是一位郁郁不得志、得不到朝廷重用的官，同时也在创作宋词"),
    HumanMessage(content = "给我写一首宋词")
]
res = llm.stream(input = messages)
for chunk in res:
    if chunk:
        print(chunk.content,end = "",flush = True)