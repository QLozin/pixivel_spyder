from pydantic import BaseModel, Field, validator
from typing import Literal, Union, Any
from json import dumps, loads
from datetime import datetime
from httpx import Response


class GeneralBaseModel(BaseModel):
    """
    扩充的基本模型，有keys,info,to_json三个方法
    : keys : 返回所有的键
    : info : 传入一个字符串或者列表，包含键名，返回一个列表包含所求的值
    : to_json : 返回一个json字符串
    """

    def keys(self) -> list:
        return list(self.dict().keys())

    def info(self, keys: Union[list[str], str]) -> list:
        _inner_dict = self.dict()
        if isinstance(keys, str):
            return [_inner_dict.get(keys, None)]
        elif isinstance(keys, list):
            return [_inner_dict.get(i, None) for i in keys]

    def to_json(self) -> dict:
        return loads(dumps(self.dict()))


class Interest(BaseModel):
    prefix: str = Field("https://pixivel.moe/illust/", description="图片地址前缀")
    imgTarget: tuple = Field(("a", {"data-v-3a4e140a": ""}), description="图片链接尾所在标签")


class _TagsInner(BaseModel):
    name: str
    translation: str = Field("", description="标签的中文翻译，有时候会没有")


class _Tags(BaseModel):
    """
    这个东西并不好用
    """

    one: _TagsInner = ""
    two: _TagsInner = ""
    three: _TagsInner = ""
    four: _TagsInner = ""
    five: _TagsInner = ""
    six: _TagsInner = ""
    seven: _TagsInner = ""
    eight: _TagsInner = ""
    nine: _TagsInner = ""


class _Statistic(BaseModel):
    bookmarks: int
    likes: int
    comments: int
    views: int


class SimpleImage(BaseModel):
    id: int
    url: str

    def join_prefix(self, prefix_url: str):
        self.url = prefix_url + self.url
        return self


class SinglePic(GeneralBaseModel):
    id: int
    title: str
    altTitle: str = Field("", description="小标题")
    description: str = ""
    type: int = 0
    createDate: str
    uploadDate: str
    sanity: int
    width: int
    height: int
    pageCount: int
    tags: list[dict] = [{}]
    statistic: _Statistic
    aiType: int
    image: Union[datetime, str]

    @validator("image", pre=True)
    def parse_image(cls, value):
        """
        一个验证器，将在Image被载入之前进行格式化，将str对象转换为datetime对象\n
        装饰器的pre参数确保了她在载入之前被验证。
        """
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return value

    def filtered(self, likes_limit: int = 0, comments_limit: int = 0, views_limit: int = 0) -> bool:
        """
        根据喜欢数、评论数、浏览数进行图片过滤
        """
        if self.statistic.likes >= likes_limit and self.statistic.comments >= comments_limit and self.statistic.views >= views_limit:
            return True
        else:
            return False

    def page_num_filter(self, page_num_filter: int = None) -> bool:
        """
        检查这P的图片数量是否符合要求，如果少于最大数量则返回True
        """
        return self.pageCount <= page_num_filter

    def keys(self) -> list:
        return ["id", "title", "altTitle", "description", "type", "createDate", "uploadDate", "sanity", "width",
                "height", "pageCount", "tags", "statistic", "aiType"]

    def get_url(self, origin_url: str = None) -> str:
        """
        返回这个图片的URL地址，默认网址前缀为https://pixivel.moe/illust/\n
        这个URL地址指明了图片所在的网页，不合适用于爬虫爬取，但是可以在浏览器内访问
        """
        _original_url = "https://pixivel.moe/illust/" if origin_url is None else origin_url
        return _original_url + str(self.id)

    def _get_img_time(self) -> str:
        """
        一个内部方法，用于序列化日期，因为API那边使用日期来定位图片\n
        将"2019-12-01T12:40:19"转换为"2019/12/01/12/40/19"以便拿到图片地址
        """
        if isinstance(self.image, str):
            return datetime.strptime(self.image, "%Y-%m-%dT%H:%M:%S").strftime("%Y/%m/%d/%H/%M/%S")
        elif isinstance(self.image, datetime):
            return self.image.strftime("%Y/%m/%d/%H/%M/%S")
        else:
            raise TypeError("image属性不是str或者datetime对象，你得看看为什么能把怪东西传进来，这个错误不应该发生的")

    def get_img(self) -> list[str]:
        """
        解析出这一个图片的API地址，如果只有一张图片则直接返回他的API字符串，否则返回列表
        """
        _times = self._get_img_time()
        _res = [_times + f"/{self.id}_p{i}_master1200.jpg" for i in range(self.pageCount)]
        return _res

    def improve_get_img(self) -> list[SimpleImage]:
        _times = self._get_img_time()
        _res = [SimpleImage(url=f"{_times}/{self.id}_p{i}_master1200.jpg", id=self.id) for i in range(self.pageCount)]
        return _res


class Page(BaseModel):
    illusts: list[SinglePic]
    has_next: bool

    @classmethod
    def loading(cls, illusts: list[dict[str, list]], has_next: bool):
        _ill = [SinglePic(**i) for i in illusts]
        return cls.parse_obj({"illusts": _ill, "has_next": has_next})

    def get_id(self, likes_limit: int = 0, comments_limit: int = 0, views_limit: int = 0) -> list[int]:
        """
        获取符合条件的图片ID
        : likes_limit : int
        : comments_limit : int
        : views_limit : int
        : return: list[int]
        """
        return [i.id for i in self.illusts if i.filtered(likes_limit, comments_limit, views_limit)]

    def get_url(self, likes_limit: int = 0, comments_limit: int = 0, views_limit: int = 0, origin_url: str = None) -> \
            list[str]:
        """
        这个方法会尝试返回一个列表，他接受爱心数、评论数、浏览数的限制，以及一个原始的网址前缀
        : likes_limit : int
        : comments_limit : int
        : views_limit : int
        : origin_url : str
        : return : list[str]
        """
        return [i.get_url(origin_url) for i in self.illusts if i.filtered(likes_limit, comments_limit, views_limit)]

    def have_next(self) -> bool:
        return self.has_next

    def get_pic_api(self, max_pic_num: int) -> list[list[str]]:
        """
        返回当前页的所有图片API地址后缀，接收一个最大图片数量参数
        : max_pic_num : int 如果该P的图片数量超过限制则不返回
        """
        return [i.get_img() for i in self.illusts if i.page_num_filter(max_pic_num)]

    def improve_get_pic_api(self, max_pic_num: int, like: int = 0, view: int = 0, comments: int = 0) -> list[
        list[SimpleImage]]:
        return [i.improve_get_img() for i in self.illusts if
                i.filtered(like, comments, view) and i.page_num_filter(max_pic_num)]


class PixivelPage(BaseModel):
    error: bool
    message: str
    data: Page = Page(**{"illusts": [], "has_next": False})

    @classmethod
    def loading(cls, html_json: dict):
        """
        加载Json数据，适配api.pixivel.moe的返回值
        : html_json : dict
        """
        if not isinstance(html_json, dict):
            raise TypeError("需要传入字典，传了个什么若智的东西进来？爬开")
        if len(html_json) == 0:
            raise ValueError("传入的字典为空，你是不是没传？")
        _error = html_json["error"]
        if _error:
            return cls.parse_obj({"error": _error, "message": html_json["message"]})
        _data = Page.loading(**html_json["data"])
        return cls.parse_obj({"error": _error, "message": html_json["message"], "data": _data})

    def get_pic_id(self, likes_limit: int = 0, comments_limit: int = 0, views_limit: int = 0) -> list[int]:
        """
        返回所有pixiv图片的ID，往往用作存档，接收三个参数，分别是喜欢数、评论数、浏览数的限制
        :return: list[int]
        """
        return self.data.get_id(likes_limit=likes_limit, comments_limit=comments_limit, views_limit=views_limit)

    def get_all_url(self, likes_limit: int = 0, comments_limit: int = 0, views_limit: int = 0,
                    origin_url: str = None) -> list[str]:
        """
        获取所有符合条件的图片的URL地址，这些地址不适合爬虫访问，适合浏览器手动访问或存档\n
        返回一个包含https地址的列表
        : likes_limit : int
        : comments_limit : int
        : views_limit : int
        : origin_url : str 网页前缀的地址，后台会直接将图片ID拼接到这个地址上，如果没有需要请不要更改
        : return : list[str]
        """
        return self.data.get_url(likes_limit, comments_limit, views_limit, origin_url)

    def have_next(self) -> bool:
        """
        指明当前页是否有下一页
        """
        return self.data.have_next()

    def _inner_get_api(self, filter_lst: dict[str, int], max_pic_num: int = 99,
                       pure_api: bool = False, prefix_url: str = None,
                       pic_size: Literal[None, "540x540_70"] = "540x540_70", improve: bool = False) -> Any:
        """
        返回当前页的所有图片API地址后缀，接收一个最大图片数量参数
        : pure_api : bool 是否只返回API地址，如果否则使用prefix_url进行拼接
        : max_pic_num : int 如果该P的图片数量超过限制则不返回，默认是99
        : prefix_url : str 网页前缀的地址，后台会直接将图片ID拼接到这个地址上，如果没有需要请不要更改
        : pic_size : str 图片尺寸，如果不填则默认为540x540_70，预览图大小
        """
        _size = "540x540_70" if pic_size is None else pic_size
        _prefix = f"https://proxy.pixivel.moe/c/{_size}/img-master/img/" if prefix_url is None else prefix_url
        if improve:
            _res = self.data.improve_get_pic_api(max_pic_num=max_pic_num, **filter_lst)
            return _res if pure_api else [si.join_prefix(_prefix) for innerList in _res for si in innerList]

        _res = self.data.get_pic_api(max_pic_num)
        return _res if pure_api else [_prefix + url for innerList in _res for url in innerList]

    def get_api(self, likes: int = 0, comments: int = 0, views: int = 0, max_pic_num: int = 99, pure_api: bool = False,
                prefix_url: str = None,
                pic_size: Literal[None, "540x540_70"] = "540x540_70") -> list[str]:
        _dict = {"like": likes, "comments": comments, "view": views}
        return self._inner_get_api(_dict, max_pic_num, pure_api, prefix_url, pic_size)

    def improve_get_api(self, likes: int = 0, comments: int = 0, views: int = 0, max_pic_num: int = 99,
                        pure_api: bool = False, prefix_url: str = None,
                        pic_size: Literal[None, "540x540_70"] = "540x540_70") -> list[SimpleImage]:
        """
        返回当前页的所有图片API地址后缀，接收按照喜欢数、评论数、浏览数的限制参数
        : likes : int
        : comments : int
        : views : int
        : pure_api : bool 是否只返回API地址，如果否则使用prefix_url进行拼接
        : max_pic_num : int 如果该P的图片数量超过限制则不返回，默认是99
        : prefix_url : str 网页前缀的地址，后台会直接将图片ID拼接到这个地址上，如果没有需要请不要更改
        : pic_size : str 图片尺寸，如果不填则默认为540x540_70，预览图大小
        : return : list[SimpleImage]，包含奇怪对象的列表
        """
        _dict = {"like": likes, "comments": comments, "view": views}
        return self._inner_get_api(_dict,max_pic_num, pure_api, prefix_url, pic_size, improve=True)


class Param(BaseModel):
    mode: Literal["illust", "user", "tag"] = "tag"
    features: Literal["sortpop", "sortdate", "sortdate,sortpop", "sortpop,sortdate"] = "sortpop"
    keyword: str
    pages: int = 0

    @classmethod
    def loading(cls, lst: Union[list, str], features: str = "sortpop", mode: str = "tag"):
        if isinstance(lst, list):
            _keyword = ",".join(lst)
        elif isinstance(lst, str):
            _keyword = lst
        else:
            raise TypeError("lst must be list or str")
        _keyword.replace("，", "").replace(" ", "")
        return cls.parse_obj({"keyword": _keyword, "features": features, "mode": mode})


class NewParam(GeneralBaseModel):
    mode: Literal["illust", "user", "tag"] = "tag"
    sortpop: bool = True
    sortdate: bool = False
    pages: int = 0


class BasicPicInfo(BaseModel):
    pic_id: int
    pic_name: str
    pic_url: str
    pic_weight: int
    pic_height: int
    MIME: str
    time: str

    @validator("pic_id", pre=True)
    def _pic_id(cls, value):
        if isinstance(value, str):
            try:
                return int(value)
            except:
                raise TypeError(f"pic_id must be int or str, now get {value}")
        else:
            return value

    @validator("pic_url", pre=True)
    def _pic_url(cls, value):
        if isinstance(value, Response):
            return str(value.url)
        elif isinstance(value, str):
            return value
        else:
            raise TypeError("pic_url must be str or Response")

    @validator("time", pre=True)
    def _time(cls, value):
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
            except:
                raise TypeError("无法将传入的时间字符串格式化为正确的时间")
        else:
            raise ValueError("传入的时间参数不正确")
