from langchain_core.prompts import PromptTemplate, FewShotPromptTemplate
from langchain_community.chat_models import ChatZhipuAI
import os

client = ChatZhipuAI(
    model = "glm-4-flash",
    api_key = os.environ["ZHIPU_API_KEY"]
)

example_template = PromptTemplate.from_template("单词：{word}, 反义词：{antonym}")

examples_data = [
    {"word": "上", "antonym": "下"},
    {"word": "前", "antonym": "后"}
]

few_shot_template = FewShotPromptTemplate(
    example_prompt = example_template,
    examples = examples_data,
    prefix = "告知我单词的反义词，我提供以下的实例",
    suffix = "根据我提供的示例告诉我，{input_word}的反义词是什么？",
    input_variables = ['input_word']
)

prompt_text = few_shot_template.invoke(input = {"input_word": "左"})
response = client.invoke(input = prompt_text)
print(response.content)