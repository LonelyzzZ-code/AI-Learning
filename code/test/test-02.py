from langchain_community.embeddings import ZhipuAIEmbeddings
import os

embed = ZhipuAIEmbeddings(
    model = "embedding-2",
    api_key = os.environ["ZHIPU_API_KEY"]
)

print(embed.embed_query("我喜欢你"))
print(embed.embed_documents(["我喜欢你", "我稀饭你", "今天网上吃什么"]))