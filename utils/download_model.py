import os
from sentence_transformers import SentenceTransformer
from config import env


def download():
    """
    下载模型
    """
    # 创建模型保存路径
    print(f"模型保存路径为 {env.MODEL_STORE_PATH}")
    os.makedirs(env.MODEL_STORE_PATH, exist_ok=True)
    # 下载并保存模型
    model = SentenceTransformer(env.MODEL_CHOOSE)
    model.save(env.MODEL_STORE_PATH)
    print(f"模型已成功下载到 {env.MODEL_STORE_PATH} 目录")