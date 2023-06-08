from httpx import Client
from typing import Union, IO
from pathlib import Path
from json import dump, loads
from loguru import logger as log
# custom loading
from Model import NewParam
from Analysis import Analyser
from http_download import Download
from SQL import MySQL_ini
from http_Selenuim import Selenium
class HttpRequest(object):
    cookies = {"_ga": "GA1.2.602616331.1684336313",
               "_ga_0VCRDCKZFV": "GS1.1.1686121224.13.1.1686121229.55.0.0",
               "_gid": "GA1.2.1298691765.1686108684"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Host": "api.pixivel.moe",
        "Connection": "keep-alive",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Accept-Encoding": "gzip, deflate, br",
    }

    def __init__(self, test_model: bool = False, cookie: dict = None) -> None:
        self.target_url = "https://api.pixivel.moe/v2/pixiv/tag/search/"
        self.test_url = "https://api.pixivel.moe/v2/pixiv/tag/search/%E7%99%BD%E4%B8%9D,%E9%BB%91%E4%B8%9D?page=0&sortpop=true&sortdate=false"
        self.http_receive = None
        self.test_model = test_model
        self.param = NewParam()
        if cookie is None:
            with Selenium(headless=False) as browser:
                self.cookie = Selenium.want_cookies(browser)
        else:
            self.cookie = cookie
    def set_sortpop(self, value: Union[bool, int]):
        log.info(f"【按热度排序】被设置为{bool(value)}")
        self.param.sortpop = bool(value)

    def set_sortdate(self, value: Union[bool, int]):
        log.info(f"【按发布日期排序】被设置为{bool(value)}")
        self.param.sortdate = bool(value)

    def next_page(self, page_num: int = None):  # type: ignore
        _next = 1 if page_num is None else page_num
        log.info(f"当前页 {self.param.pages} 前往 {_next} 页")
        self.param.pages += _next

    def request(self, tags: Union[str, list]):
        _process = ",".join(tags) if isinstance(tags, list) else tags
        log.info(f"处理传入的标签{_process}")
        _process = _process.replace(" ", "").replace("，", "")
        log.info(f"检查tag中没有异常字符::{_process}")
        _url = self.test_url if self.test_model else self.target_url + _process
        with Client(cookies=self.cookie) as client:
            self.http_receive = client.get(_url, headers=HttpRequest.headers, params=self.param.dict())
        log.warning(f"检查请求的网址{self.http_receive.url}")
        log.debug(f"检查请求状态{self.http_receive.status_code}")

    def get_result(self) -> dict:
        if self.http_receive is None:
            log.warning(f"当前还没有获得内容")
            return {}
        else:
            return self.http_receive.json()

    def save_receive(self, path: Union[Path, str, IO], file_name: str = "") -> dict:
        """
        保存方法，将获得的请求数据保存到指定路径的指定文件中
        : path: 保存文件路径，可以是Path对象，也可以是字符串，也可以是文件句柄
        : file_name: 保存文件名，如果为空，则按照path的路径和文件名保存
        """
        if self.http_receive is None:
            log.critical(f"当前还没有获得内容")
            return {}
        if isinstance(path, IO):
            dump(self.http_receive.json(), path, ensure_ascii=False, indent=4)
            log.success(f"内容已经写入传入的句柄")
            return {}
        _path = Path(path) / file_name
        _mode = "w" if _path.exists() and _path.is_file() else "a"
        with open(str(_path.absolute()), _mode, encoding="utf8") as _f:
            dump(self.http_receive.json(), _f, ensure_ascii=False, indent=4)
            log.success(f"内容已经写入{_path.absolute()}")
            return self.http_receive.json()

    def main(self, tags: Union[list, str], save_file: str = ""):
        self.request(tags)
        if save_file != "":
            re = self.save_receive(save_file)
            return re


if __name__ == '__main__':
    SQ = MySQL_ini
    SQ.initialize()
    # Re = HttpRequest()
    # Re.main(["落日","夕阳"], "./FinalTest.json")
    with open("./FinalTest.json","r",encoding='utf-8') as f:
        _res = f.read()
    #res = dumps(_res, ensure_ascii=False, indent=4)
    res = loads(_res)
    An = Analyser
    re_json = An.load_json(res)
    re_pic = An.load_pic(re_json).improve_get_api(likes=400)
    log.warning(f"检查图片链接{re_pic[:3]}检查状态{type(re_pic[0])}")
    Dn = Download(re_pic, r"G:\Python爬虫课设预览图保存处\download")
    Dn.down_run()
    #获取已经下载的图片信息
    data_info = Dn.pic_info
    SQ.write_dict(data_info)