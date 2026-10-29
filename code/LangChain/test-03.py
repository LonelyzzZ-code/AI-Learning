from langchain_community.chat_models import ChatZhipuAI
from langchain_core.prompts import PromptTemplate
import os

prompt_template = PromptTemplate.from_template(
    "我的领居姓{lastname},刚生了{gender},你帮我起个名字，简单回答"
)

client = ChatZhipuAI(
    model = "glm-4-flash",
    api_key = os.environ["ZHIPU_API_KEY"]
)

chain = prompt_template | client #构建langchain执行链条
resp = chain.invoke(input = {"lastname": "蒋", "gender": "男孩"})
print(resp.content)