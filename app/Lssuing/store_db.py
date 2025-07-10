import sqlite3
import os

class Store_db:
    """
    存储数据库，，用来存储授权的群，功能和时间
    """
    def __init__(self):
        pass
    def __str__(self):
        return "create database for admin and user"

if __name__ == '__main__':
    print(Store_db())