from httpx import AsyncClient, HTTPError, Response
from typing import Union
from pathlib import Path
import asyncio
from loguru import logger as log
from urllib.parse import urlparse
from datetime import datetime
# custom loading
from other_function import parse_image
from Model import BasicPicInfo, SimpleImage
from SQL import MySQL_ini

class Download(object):
    header = {"Accept":
                  "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
              "Accept-Encoding": "gzip, deflate, br",
              "Host": "proxy.pixivel.moe",
              "User-Agent": "Mozilla/5.0 (Linux; Android 5.0) AppleWebKit/537.36 (KHTML, like Gecko) Mobile Safari/537.36 (compatible; Bytespider; https://zhanzhang.toutiao.com/)"}

    def __init__(self, download_lst: Union[str, list[str], list[SimpleImage]],
                 file_path: Union[str, Path] = "./download",
                 error_limit: int = 10):
        self.download_lst, self.download_url = None, None
        if isinstance(download_lst, str):
            log.info(f"接收到下载地址::{download_lst}")
            self.download_url = download_lst
        elif isinstance(download_lst, list):
            log.info(f"接收到下载列表，抽检类型{type(download_lst[0])}，抽检内容{download_lst[0]}")
            self.download_lst = download_lst
        else:
            log.critical(f"严重的初始化传参错误")
            raise TypeError("download_lst must be str or list[str]")
        self.pic_num = 0
        self.file_path = self._check_path(file_path)
        self.error_num = 0
        self.error_limit = error_limit
        self.sql = MySQL_ini
        self.pic_info: list[BasicPicInfo] = []

    @log.catch
    async def _down(self, target_url: Union[str, SimpleImage] = None,
                    target_lst: Union[list[str], list[SimpleImage]] = None,
                    base_url: str = "https://proxy.pixivel.moe/c/540x540_70/img-master/img/"):
        if target_url is None and target_lst is None:
            log.critical(f"错误的传参必须被阻止，你不能同时两个参数都传入None!")
            return None
        async with AsyncClient(headers=Download.header, base_url=base_url) as AClient:
            try:
                if target_url:
                    _target_url = target_url.url if isinstance(target_url, SimpleImage) else target_url
                    log.info(f"尝试请求::{_target_url}")
                    if self.sql.url_exists(_target_url):
                        log.warning(f"数据库中已存在该图片，跳过下载")
                        return None
                    response = await AClient.get(_target_url)
                    log.success(f"请求完成")
                    self._downloader_save_file(response, target_url)
                elif target_lst:
                    for _url in target_lst:
                        log.debug(
                            f"传入{type(target_url)}是SimpleImage吗?::{isinstance(target_url, SimpleImage)}")
                        _use_url = _url.url if isinstance(_url, SimpleImage) else _url
                        log.info(f"尝试请求::{_use_url}")
                        if self.error_num > self.error_limit:
                            log.warning(f"当前累计错误已经超过限制，停止下载")
                            break
                        if self.sql.url_exists(_use_url):
                            log.warning(f"数据库中已存在该图片，跳过下载")
                            continue
                        response = await AClient.get(_use_url)
                        log.success(f"请求完成")
                        self._downloader_save_file(response, _url)
            except HTTPError as e:
                self.error_num += 1
                log.error(f"请求异常->{e}<-累计错误{self.error_num}次")
                if self.error_num > self.error_limit:
                    log.critical(f"当前累计错误已经超过限制，停止下载")
                    return None

    async def _manager(self):
        tasks = []
        if self.download_lst:
            log.debug(f"检测到下载列表有效，{self.download_lst}")
            for _url in self.download_lst:
                if isinstance(_url, Union[str, SimpleImage]):
                    tasks.append(self._down(target_url=_url))
                elif isinstance(_url, list):
                    tasks.append(self._down(target_lst=_url))
                else:
                    log.warning(f"下载列表中存在非法的下载地址::{type(_url)}")
            await asyncio.gather(*tasks)
        elif self.download_url:
            await asyncio.run(self._down(target_url=self.download_url))
        else:
            log.critical(f"严重的初始化传参错误")

    def down_run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._manager())
        loop.close()

    def _downloader_save_file(self, response: Response, self_img: SimpleImage = None):
        if response.status_code != 200:
            log.warning(f"请求失败::{'资源不存在' if response.status_code == 404 else '未知错误'}")
            self.error_num += 1
        self.pic_num += 1
        file_name = self._get_file_name(response)
        with open(self.file_path / file_name, "wb") as f:
            f.write(response.content)
            log.info(f"写入完成::{response.url}")
        _self_img = self_img if isinstance(self_img, SimpleImage) else None
        log.info(f"开始解析图片信息::{_self_img.id if isinstance(self_img, SimpleImage) else '图片ID为空'}")
        pic_info = parse_image(response.content)
        _dict = {"pic_id": 0 if _self_img is None else _self_img.id, "pic_name": file_name,
                 "pic_url": str(response.url), "time": datetime.now()} | pic_info
        log.debug(f"尝试装填{_dict}")
        self.pic_info.append(BasicPicInfo(**_dict))

    def _get_file_name(self, response: Response):
        content_disposition = response.headers.get("Content-Disposition")
        if content_disposition:
            parts = content_disposition.split(";")
            for part in parts:
                if part.strip().startswith("filename="):
                    return part.split("=")[1].strip('"')
        else:
            name_url = urlparse(str(response.url)).path
            filename = name_url.split('/')[-1]
            if filename != "":
                return filename
        return f"unknown_{self.pic_num}.jpg"

    @staticmethod
    def _check_path(f_path: Union[str, Path], force: bool = False) -> bool:
        if not isinstance(f_path, (str, Path)):
            f_path = "./download"
        _path = Path(f_path)
        if not force:
            i = 1
            while _path.is_dir():
                mid = _path.name.split("_")[0]
                _path = _path.parent / f"{mid}_{i}"
                i += 1
            _path.mkdir(parents=True, exist_ok=True)
        return _path


if __name__ == '__main__':
    url = "https://proxy.pixivel.moe/c/540x540_70/img-master/img/2020/09/10/01/52/10/84270641_p0_master1200.jpg"
    url_2 = "https://proxy.pixivel.moe/c/540x540_70/img-master/img/2019/12/01/12/40/19/78083043_p0_master1200.jpg"
    Dn = Download([url, url_2], "./test_download")

