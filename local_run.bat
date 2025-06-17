call .venv/Scripts/activate

python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

pip install .

python utils/Create_dirs.py

pip install .

python utils/DataMigrator.py

pip install .

python main.py