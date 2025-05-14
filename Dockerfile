FROM python:3.10.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
RUN pip install .

COPY . .

EXPOSE 3001

CMD ["sh","-c""python utils/DataMigrator.py && python main.py"]