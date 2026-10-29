from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
import os

client = ChatZhipuAI(
    model = "glm-4-flash",
    api_key = os.environ["ZHIPU_API_KEY"],
)

prompt_template = PromptTemplate(
    template="你需要根据用户对话历史回答问题，对话历史：{history}，用户问题：{input}"
)

str_parser = StrOutputParser()

chain = prompt_template | client | str_parser

store = {}

def get_history(session_id):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

new_chain = RunnableWithMessageHistory(
    chain,
    get_history,
    history_messages_key = "history",
    input_messages_key = "input"
)

if __name__ == '__main__' :
    session_config = {
        "configurable": {
            "session_id": "user_001"
        }
    }

res = new_chain.invoke({"input": "小明有两条狗"}, session_config)
print(f"第一次输出：{res}")
res = new_chain.invoke({"input": "小明有一只猫"}, session_config)
print(f"第二次输出：{res}")
res = new_chain.invoke({"input": "小明有几只宠物？"}, session_config)
print(f"第三次输出：{res}")