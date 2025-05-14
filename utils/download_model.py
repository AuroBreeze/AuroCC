import os
from sentence_transformers import SentenceTransformer

# 创建模型保存路径
os.makedirs('./local_model', exist_ok=True)

# 下载并保存模型
model = SentenceTransformer('distilbert-base-nli-stsb-mean-tokens')
model.save('./local_model')
print("模型已成功下载到 ./local_model 目录")