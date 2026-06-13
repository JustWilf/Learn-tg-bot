# This is a complete SQLite database controller, as far as a bot needs it
from pathlib import Path
import sqlite3 as sql


class Adding:
    CONNECTION: sql.Connection = sql.connect(Path(__file__).resolve().parent.parent / "sqlite.db")

class Removing:
    CONNECTION: sql.Connection = sql.connect(Path(__file__).resolve().parent.parent / "sqlite.db")

class Editing:
    CONNECTION: sql.Connection = sql.connect(Path(__file__).resolve().parent.parent / "sqlite.db")