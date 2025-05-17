# 阿里云镜像示例
FROM python:3.10.12-slim

WORKDIR /app

COPY requirements.txt .


RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

COPY . .

RUN pip install .

EXPOSE 3001

RUN python utils/DataMigrator.py


CMD ["python","main.py"]