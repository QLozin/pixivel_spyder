from bs4 import BeautifulSoup as bs
from typing import Union
from loguru import logger as log
from json import loads, load
from pathlib import Path
# custom loading
from Model import PixivelPage


class Analyser(object):

    def __init__(self, html_receive: Union[dict, str] = None):  # type: ignore
        if html_receive is None:
            self.html_receive = None
            return
        if isinstance(html_receive, dict):
            self.data = Analyser.load_pic(html_receive)
        else:
            self.data = Analyser.load_pic(Analyser.load_json(html_receive))

    @staticmethod
    def deep_find(target_pool: Union[tuple, list], html_text: str):
        """
        这个方法将尝试把一个HTML文本解析为BeautifulSoup对象，然后根据传入的参数进行递归查找感兴趣的标签\n
        你可以嵌套的传入可迭代对象，然后递归查找
        这个方法似乎已经被弃用
        : target_pool : 一个可迭代对象，要求第一个参数是标签名，第二个参数是他的属性，这个属性以字典表现，如["a,{"class":"test"}]将查找有这个class值的a标签
        : html_text : str HTML的纯文本对象，需要能被BeautifulSoup解析
        """

        def _resolution(soup_ob: bs, target: Union[tuple[str, dict], list[str, dict]]):
            return soup_ob.find(*target)

        _soup = bs(html_text, "lxml")
        clk = 0
        while clk < len(target_pool):
            log.info(f"正在解析第{clk + 1}层")
            _soup = _resolution(_soup, target_pool[clk])
            clk += 1
        return _soup

    @staticmethod
    def load_json(html_text: Union[Path, str]) -> dict:
        """
        这个方法将把一个可能是路径的字符串、路径Path对象、JSON字符串格式化为JSON对象返回
        """
        log.info(f"尝试解析JSON")
        if isinstance(html_text, Path):
            if html_text.exists() and html_text.is_file:
                try:
                    log.debug(f"路径{html_text}存在且是文件，尝试解析")
                    with open(html_text.absolute(), "r", encoding="utf8") as _f:
                        log.success("成功解析JSON文件")
                        return load(_f)
                except Exception as e:
                    log.critical(f"意外错误::{e}")
                    return {}
            else:
                log.error(f"文件{html_text}不存在")
                return {}
        elif isinstance(html_text, str):
            log.debug(f"检测到传入参数是字符串，尝试解析")
            _re = loads(html_text)
            if isinstance(_re, dict):
                log.success("成功解析JSON字符串")
                return _re
            else:
                log.error(f"JSON解析失败::{type(_re)}")
                return {}
        elif isinstance(html_text, dict):
            log.warning(f"传入的参数不正确，似乎传入了一个JSON文件")
            return html_text
        else:
            log.critical(f"意外的参数")
            raise TypeError(f"意外的参数类型::{type(html_text)}")

    @staticmethod
    def load_pic(pic_json: dict) -> PixivelPage:
        """
        这个方法将把一个JSON|字典对象装载入PixivelPage对象中
        """
        return PixivelPage.loading(pic_json)


if __name__ == '__main__':
    An = Analyser
    file_path = Path("./receiveHTML.json")
    if file_path.exists() and file_path.is_file():
        with open(str(file_path.resolve()), "r", encoding="utf8") as f:
            res = An.load_json(f.read())
        parse_json = An.load_pic(res)
        print(parse_json.get_all_url(likes_limit=2000))
    else:
        print("寄")
