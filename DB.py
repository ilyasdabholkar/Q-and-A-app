from sqlite3.dbapi2 import connect
from flask import g
import sqlite3
import os

url = os.getcwd().replace("\\","/") + '/local.db'

#establish connection to database
def connect_db():
    db = sqlite3.connect(url)
    db.row_factory = sqlite3.Row
    return db

#access database
def get_db():
    if not hasattr(g,'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db
