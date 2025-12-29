from pydantic import Field

from .base import APIModel


class DownloadFromShare(APIModel):
    """
    从“分享文本/分享链接”解析并下载。

    - text: 允许包含整段分享文案（里面含链接即可）
    - mark: 可选，自定义归档标识（用于文件夹命名）
    - cursor/count: 主要用于合集中分页（不传则用默认值）
    """

    text: str
    mark: str = ""
    cursor: int = 0
    count: int = Field(12, gt=0)


class DownloadFromShareTikTok(DownloadFromShare):
    # TikTok 合辑接口默认 count 更大
    count: int = Field(30, gt=0)


class DownloadFavorite(APIModel):
    """
    下载账号“喜欢”列表（抖音）。

    - 优先使用 sec_user_id；如果不传，可以传 text（账号主页/分享链接）让服务端自动提取 sec_user_id
    """

    sec_user_id: str = ""
    text: str = ""
    mark: str = ""
    earliest: str | float | int = ""
    latest: str | float | int = ""
    pages: int | None = None
    cursor: int = 0
    count: int = Field(18, gt=0)


class DownloadFavoriteTikTok(DownloadFavorite):
    count: int = Field(16, gt=0)

