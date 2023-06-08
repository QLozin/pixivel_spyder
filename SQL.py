import sqlite3 as sql
from loguru import logger as log
from Model import BasicPicInfo


class MySQL(object):
    def __init__(self, db_name: str = "default.db"):
        self.conn = sql.connect(db_name)
        self.is_initialize: bool = False

    def initialize(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("CREATE TABLE IF NOT EXISTS image_save("
                           "`uuid` INTEGER PRIMARY KEY NOT NULL,"
                           "`pid` INTEGER NOT NULL,`url` VARCHAR(255),`pname` VARCHAR(64),"
                           "`pweight` INT,`pheight` INT,`MIME` VARCHAR(12),`time` DATETIME)")
            self.conn.commit()
            log.success(f"初始化数据库成功或已经初始化")
            self.is_initialize = True
            return True
        except Exception as e:
            log.critical(f"初始化数据库失败::{e}")
            self.conn.rollback()
            return False

    def _insert(self, pic_id: int, pic_name: str, pic_weight: int, pic_height: int, MIME: str, time: str, pic_url: str):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO image_save(`uuid`,`pid`,`url`,`pname`,`pweight`,`pheight`,`MIME`,`time`)"
                           "VALUES(?,?,?,?,?,?,?,?)",
                           (None, pic_id, pic_url, pic_name, pic_weight, pic_height, MIME, time))
            self.conn.commit()
            log.success(
                f"插入数据成功，插入数据为({pic_id},{pic_url},{pic_name},{pic_weight},{pic_height},{MIME},{time})")
            return True
        except Exception as e:
            log.critical(f"插入数据失败::{e}数据库回滚")
            self.conn.rollback()
            return False

    def write_dict(self, data: list[BasicPicInfo]):
        if self.is_initialize:
            [log.success(f"{BPI.pic_id}数据插入成功") for BPI in data if self._insert(**BPI.dict())]
        else:
            log.critical(f"数据未初始化，即时这样，也要插入表吗？")

    def _select(self, col_name: str, condition: str):
        if self.is_initialize:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT {col_name} FROM image_save WHERE {condition}")
            return cursor.fetchall()
        else:
            log.warning(f"数据未初始化，默认放行")
            return True

    def pid_exists(self, pid: str):
        return True if self._select("pid", f"pid = '{pid}'") else False

    def url_exists(self, url: str):
        return True if self._select("url", f"url = '{url}'") else False


MySQL_ini = MySQL()
