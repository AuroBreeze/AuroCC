import os
from sentence_transformers import SentenceTransformer
from config import dev
# 创建模型保存路径
print(f"模型保存路径为 {dev.MODEL_STORE_PATH}")
os.makedirs(dev.MODEL_STORE_PATH, exist_ok=True)
# 下载并保存模型

model = SentenceTransformer(dev.MODEL_CHOOSE)
model.save(dev.MODEL_STORE_PATH)
print(f"模型已成功下载到 {dev.MODEL_STORE_PATH} 目录")