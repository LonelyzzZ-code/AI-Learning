from langchain_community.chat_models import ChatZhipuAI
from langchain_core.output_parsers import StrOutputParser,JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
import os

client = ChatZhipuAI(
    model = "glm-4-flash",
    api_key = os.environ["ZHIPU_API_KEY"]
)

prompt_template_01 = PromptTemplate.from_template(
    "我的邻居姓{lastname}, 刚生了{gender}, 请你给他起一个名字, 请严格按照JSON格式输出，key是name，value就是你起的名字"
)

prompt_template_02 = PromptTemplate.from_template(
    "这是我起的名字{name}，请解析"
)

parser_01 = StrOutputParser()
parser_02 = JsonOutputParser()

my_function = RunnableLambda(lambda ai_msg:{"name": ai_msg.content})

chain = prompt_template_01 | client | parser_02 | prompt_template_02 | client | parser_01
for chunk in chain.stream({"lastname": "伍", "gender": "男孩"}):
    if chunk:
        print(chunk, end = "", flush = True)

