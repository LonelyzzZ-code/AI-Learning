from langchain_community.chat_models import ChatZhipuAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
import os

client = ChatZhipuAI(
    model = "glm-4-flash",
    api_key = os.environ["ZHIPU_API_KEY"]
)

prompt_template = PromptTemplate.from_template(
    "我的邻居姓{lastname}, 刚生了{gender}, 请你给他起一个名字"
)

parser = StrOutputParser()
chain = prompt_template | client | parser | client | parser
for chunk in chain.stream({"lastname": "伍", "gender": "男孩"}):
    if chunk:
        print(chunk, end = "", flush = True)

