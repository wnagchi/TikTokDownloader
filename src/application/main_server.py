import asyncio
import os
from textwrap import dedent
from typing import TYPE_CHECKING

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import httpx
from uvicorn import Config, Server

from ..custom import (
    __VERSION__,
    REPOSITORY,
    SERVER_HOST,
    SERVER_PORT,
    VERSION_BETA,
    is_valid_token,
)
from ..models import (
    Account,
    AccountTiktok,
    Comment,
    DataResponse,
    Detail,
    DetailTikTok,
    GeneralSearch,
    Live,
    LiveSearch,
    LiveTikTok,
    Mix,
    MixTikTok,
    Reply,
    Settings,
    ShortUrl,
    DownloadFromShare,
    DownloadFromShareTikTok,
    DownloadFavorite,
    DownloadFavoriteTikTok,
    UrlResponse,
    UserSearch,
    VideoSearch,
)
from ..translation import _
from .main_terminal import TikTok

if TYPE_CHECKING:
    from ..config import Parameter
    from ..manager import Database

__all__ = ["APIServer"]


def token_dependency(token: str = Header(None)):
    if not is_valid_token(token):
        raise HTTPException(
            status_code=403,
            detail=_("验证失败！"),
        )


class APIServer(TikTok):
    def __init__(
        self,
        parameter: "Parameter",
        database: "Database",
        server_mode: bool = True,
    ):
        super().__init__(
            parameter,
            database,
            server_mode,
        )
        self.server = None

    async def handle_redirect(self, text: str, proxy: str = None) -> str:
        return await self.links.run(
            text,
            "",
            proxy,
        )

    async def handle_redirect_tiktok(self, text: str, proxy: str = None) -> str:
        return await self.links_tiktok.run(
            text,
            "",
            proxy,
        )

    async def run_server(
        self,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info",
    ):
        self.server = FastAPI(
            debug=VERSION_BETA,
            title="DouK-Downloader",
            version=__VERSION__,
        )
        self.setup_routes()
        # 让下载后的文件可通过 HTTP 访问：/files/<relative_path>
        # 挂载目录为 parameter.root（默认是项目 Volume 目录）
        self.server.mount(
            "/files",
            StaticFiles(directory=str(self.parameter.root), check_dir=False),
            name="files",
        )
        config = Config(
            self.server,
            host=host,
            port=port,
            log_level=log_level,
        )
        server = Server(config)
        await server.serve()

    def _path_to_file_url(self, request: Request, path: Path) -> str | None:
        """把本地路径转换成 /files 可访问 URL（仅允许 parameter.root 目录内的文件）。"""
        try:
            rel = path.resolve().relative_to(self.parameter.root.resolve())
        except Exception:
            return None
        # request.base_url 末尾带 /
        return f"{request.base_url}files/{rel.as_posix()}"

    def _predict_download_files(self, item: dict, root: Path) -> list[Path]:
        """基于 downloader 的命名规则，预测该作品下载后的文件路径列表。"""
        name = self.downloader.generate_detail_name(item)
        temp_root, actual_root = self.downloader.deal_folder_path(
            root,
            name,
            self.downloader.folder_mode,
        )
        files: list[Path] = []
        t = item.get("type")
        downloads = item.get("downloads") or []
        if t == _("图集"):
            files.extend(
                actual_root.with_name(f"{name}_{i}.jpeg") for i in range(1, len(downloads) + 1)
            )
        elif t == _("实况"):
            files.extend(
                actual_root.with_name(f"{name}_{i}.mp4") for i in range(1, len(downloads) + 1)
            )
        elif t == _("视频"):
            files.append(actual_root.with_name(f"{name}.mp4"))
        return files

    @staticmethod
    def _sanitize_hook_params(params: dict) -> dict:
        """避免把敏感字段（如 cookie）通过 webhook 外发。"""
        if not isinstance(params, dict):
            return {}
        cleaned = dict(params)
        for k in ("cookie", "cookie_tiktok", "headers", "authorization", "token"):
            cleaned.pop(k, None)
        return cleaned

    @staticmethod
    def _get_post_download_hook_urls() -> list[str]:
        """
        下载完成后的 webhook 通知地址，使用 ; 分隔多个。
        环境变量：POST_DOWNLOAD_WEBHOOK_URL
        """
        raw = (os.getenv("POST_DOWNLOAD_WEBHOOK_URL") or "").strip()
        if not raw:
            return []
        return [u.strip() for u in raw.split(";") if u.strip()]

    def _trigger_post_download_hook(self, payload: dict) -> None:
        """异步触发下载完成钩子；失败不影响主流程。"""
        if not self._get_post_download_hook_urls():
            return
        try:
            asyncio.create_task(self._send_post_download_webhook(payload))
        except RuntimeError:
            # 没有运行中的 event loop（极少见），直接忽略
            return

    async def _send_post_download_webhook(self, payload: dict) -> None:
        urls = self._get_post_download_hook_urls()
        if not urls:
            return

        token = (os.getenv("POST_DOWNLOAD_WEBHOOK_TOKEN") or "").strip()
        timeout_s = float(os.getenv("POST_DOWNLOAD_WEBHOOK_TIMEOUT", "2.0") or "2.0")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            for url in urls:
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    self.logger.info(f"已通知下载后钩子: {url}")
                except Exception as e:
                    self.logger.error(f"下载后钩子通知失败: {url} -> {e}")

    def setup_routes(self):
        @self.server.get(
            "/",
            summary=_("访问项目 GitHub 仓库"),
            description=_("重定向至项目 GitHub 仓库主页"),
            tags=[_("项目")],
        )
        async def index():
            return RedirectResponse(url=REPOSITORY)

        @self.server.get(
            "/token",
            summary=_("测试令牌有效性"),
            description=_(
                dedent("""
                项目默认无需令牌；公开部署时，建议设置令牌以防止恶意请求！
                
                令牌设置位置：`src/custom/function.py` - `is_valid_token()`
                """)
            ),
            tags=[_("项目")],
            response_model=DataResponse,
        )
        async def handle_test(token: str = Depends(token_dependency)):
            return DataResponse(
                message=_("验证成功！"),
                data=None,
                params=None,
            )

        @self.server.post(
            "/settings",
            summary=_("更新项目全局配置"),
            description=_(
                dedent("""
                更新项目配置文件 settings.json
                
                仅需传入需要更新的配置参数
                
                返回更新后的全部配置参数
                """)
            ),
            tags=[_("配置")],
            response_model=Settings,
        )
        async def handle_settings(
            extract: Settings, token: str = Depends(token_dependency)
        ):
            await self.parameter.set_settings_data(extract.model_dump())
            return Settings(**self.parameter.get_settings_data())

        @self.server.get(
            "/settings",
            summary=_("获取项目全局配置"),
            description=_("返回项目全部配置参数"),
            tags=[_("配置")],
            response_model=Settings,
        )
        async def get_settings(token: str = Depends(token_dependency)):
            return Settings(**self.parameter.get_settings_data())

        @self.server.post(
            "/douyin/share",
            summary=_("获取分享链接重定向的完整链接"),
            description=_(
                dedent("""
                **参数**:
                
                - **text**: 包含分享链接的字符串；必需参数
                - **proxy**: 代理；可选参数
                """)
            ),
            tags=[_("抖音")],
            response_model=UrlResponse,
        )
        async def handle_share(
            extract: ShortUrl, token: str = Depends(token_dependency)
        ):
            if url := await self.handle_redirect(extract.text, extract.proxy):
                return UrlResponse(
                    message=_("请求链接成功！"),
                    url=url,
                    params=extract.model_dump(),
                )
            return UrlResponse(
                message=_("请求链接失败！"),
                url=None,
                params=extract.model_dump(),
            )

        @self.server.post(
            "/douyin/download/share",
            summary=_("从分享链接解析并下载作品/图集/合集"),
            description=_(
                dedent("""
                传入“分享文案/分享链接”，接口将自动判断是单作品还是合集，并执行下载。

                下载完成后返回可访问的文件 URL（需要保持 API 服务运行）。
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_download_share(
            extract: DownloadFromShare,
            request: Request,
            token: str = Depends(token_dependency),
        ):
            resolved = await self.handle_redirect(extract.text, extract.proxy)

            # 先尝试按“合集/作品二选一”解析
            mix_flag, ids = await self.links.run(extract.text, "mix", extract.proxy)  # type: ignore[misc]
            if not ids:
                # 再尝试单作品
                ids = await self.links.run(extract.text, "detail", extract.proxy)  # type: ignore[assignment]
                mix_flag = False

            if not ids:
                return DataResponse(
                    message=_("解析分享链接失败！"),
                    data={"resolved_url": resolved, "items": []},
                    params=extract.model_dump(),
                )

            # 执行下载（先走 api=True 拿到抽取后的结构化数据，再调用 downloader 落盘）
            items_out = []
            if mix_flag:
                for mix_id in ids:
                    data = await self.deal_mix_detail(
                        True,
                        mix_id,
                        api=True,
                        source=False,
                        cookie=extract.cookie,
                        proxy=extract.proxy,
                        cursor=extract.cursor,
                        count=extract.count,
                    )
                    if not data:
                        continue
                    mix_title = (data[0] or {}).get("mix_title", "")
                    root = self.downloader.storage_folder("mix", mix_id, extract.mark or mix_title)
                    await self.downloader.run_batch(
                        data,
                        False,
                        mode="mix",
                        mark=extract.mark,
                        mix_id=mix_id,
                        mix_title=mix_title,
                    )
                    for item in data:
                        files = self._predict_download_files(item, root)
                        items_out.append(
                            {
                                "id": item.get("id"),
                                "type": item.get("type"),
                                "files": [
                                    {"path": str(p.resolve()), "url": self._path_to_file_url(request, p)}
                                    for p in files
                                ],
                            }
                        )
            else:
                root, params, logger = self.record.run(self.parameter)
                async with logger(root, console=self.console, **params) as record:
                    data = await self._handle_detail(
                        ids,
                        False,
                        record,
                        api=True,
                        source=False,
                        cookie=extract.cookie,
                        proxy=extract.proxy,
                    )
                if data:
                    root = self.downloader.storage_folder("detail")
                    await self.downloader.run_general(data, False)
                    for item in data:
                        files = self._predict_download_files(item, root)
                        items_out.append(
                            {
                                "id": item.get("id"),
                                "type": item.get("type"),
                                "files": [
                                    {"path": str(p.resolve()), "url": self._path_to_file_url(request, p)}
                                    for p in files
                                ],
                            }
                        )

            data_payload = {
                "resolved_url": resolved,
                "mount": "/files",
                "root": str(self.parameter.root.resolve()),
                "items": items_out,
            }
            self._trigger_post_download_hook(
                {
                    "event": "download.completed",
                    "platform": "douyin",
                    "source": "share",
                    "resolved_url": resolved,
                    "root": data_payload["root"],
                    "items": items_out,
                    "params": self._sanitize_hook_params(extract.model_dump()),
                }
            )
            return DataResponse(
                message=_("下载任务已完成！"),
                data=data_payload,
                params=extract.model_dump(),
            )

        @self.server.post(
            "/douyin/download/favorite",
            summary=_("下载账号喜欢作品(抖音)"),
            description=_(
                dedent("""
                下载指定账号的“喜欢”列表作品，并返回可访问文件 URL。
                
                - 传 sec_user_id：直接下载该账号喜欢列表
                - 或传 text：账号主页/分享链接（服务端会自动提取 sec_user_id）
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_download_favorite(
            extract: DownloadFavorite,
            request: Request,
            token: str = Depends(token_dependency),
        ):
            sec_user_id = extract.sec_user_id
            resolved = ""
            if not sec_user_id:
                # 1) 允许用账号主页/分享链接自动提取
                if extract.text:
                    resolved = await self.handle_redirect(extract.text, extract.proxy)
                    ids = await self.links.run(extract.text, "user", extract.proxy)  # type: ignore[misc]
                    sec_user_id = ids[0] if ids else ""
                # 2) 不传 text / sec_user_id 时，默认使用 settings.json 的 owner_url（视为“当前账号”）
                if not sec_user_id:
                    owner = (self.parameter.settings.read() or {}).get("owner_url") or {}
                    sec_user_id = owner.get("sec_uid") or owner.get("sec_user_id") or ""
                    if not sec_user_id and owner.get("url"):
                        ids = await self.links.run(owner["url"], "user", extract.proxy)  # type: ignore[misc]
                        sec_user_id = ids[0] if ids else ""

            if not sec_user_id:
                return DataResponse(
                    message=_(
                        "参数错误：缺少 sec_user_id！请传 sec_user_id 或 text；"
                        "或在 settings.json 设置 owner_url.url / owner_url.sec_uid 作为默认账号。"
                    ),
                    data={"resolved_url": resolved, "items": []},
                    params=extract.model_dump(),
                )

            info = await self.get_user_info_data(
                False,
                extract.cookie,
                extract.proxy,
                sec_user_id=sec_user_id,
            )
            if not info:
                return DataResponse(
                    message=_("获取账号信息失败，请检查 Cookie 登录状态！"),
                    data={"resolved_url": resolved, "items": []},
                    params=extract.model_dump(),
                )

            account_data, earliest, latest = await self._get_account_data(
                cookie=extract.cookie,
                proxy=extract.proxy,
                sec_user_id=sec_user_id,
                tab="favorite",
                earliest=extract.earliest,
                latest=extract.latest,
                pages=extract.pages,
                cursor=extract.cursor,
                count=extract.count,
            )
            if not any(account_data):
                return DataResponse(
                    message=_("获取喜欢作品数据失败！"),
                    data={"resolved_url": resolved, "items": []},
                    params=extract.model_dump(),
                )

            # 抽取结构化数据
            data = await self._batch_process_detail(
                account_data,
                api=True,
                tiktok=False,
                info=info,
                mode="favorite",
                mark=extract.mark,
                user_id=sec_user_id,
                earliest=earliest,
                latest=latest,
            )
            if not data:
                return DataResponse(
                    message=_("提取作品数据失败！"),
                    data={"resolved_url": resolved, "items": []},
                    params=extract.model_dump(),
                )

            # 执行下载
            folder_name = extract.mark or info.get("nickname", "")
            root = self.downloader.storage_folder("favorite", sec_user_id, folder_name)
            await self.downloader.run_batch(
                data,
                False,
                mode="favorite",
                mark=extract.mark,
                user_id=sec_user_id,
                user_name=info.get("nickname", ""),
            )

            items_out = []
            for item in data:
                files = self._predict_download_files(item, root)
                items_out.append(
                    {
                        "id": item.get("id"),
                        "type": item.get("type"),
                        "files": [
                            {"path": str(p.resolve()), "url": self._path_to_file_url(request, p)}
                            for p in files
                        ],
                    }
                )

            data_payload = {
                "resolved_url": resolved,
                "mount": "/files",
                "root": str(self.parameter.root.resolve()),
                "earliest": str(earliest),
                "latest": str(latest),
                "items": items_out,
            }
            self._trigger_post_download_hook(
                {
                    "event": "download.completed",
                    "platform": "douyin",
                    "source": "favorite",
                    "resolved_url": resolved,
                    "root": data_payload["root"],
                    "earliest": data_payload["earliest"],
                    "latest": data_payload["latest"],
                    "items": items_out,
                    "params": self._sanitize_hook_params(extract.model_dump()),
                }
            )
            return DataResponse(
                message=_("下载任务已完成！"),
                data=data_payload,
                params=extract.model_dump(),
            )

        @self.server.post(
            "/douyin/detail",
            summary=_("获取单个作品数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **detail_id**: 抖音作品 ID；必需参数
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_detail(
            extract: Detail, token: str = Depends(token_dependency)
        ):
            return await self.handle_detail(extract, False)

        @self.server.post(
            "/douyin/account",
            summary=_("获取账号作品数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **sec_user_id**: 抖音账号 sec_uid；必需参数
                - **tab**: 账号页面类型；可选参数，默认值：`post`
                - **earliest**: 作品最早发布日期；可选参数
                - **latest**: 作品最晚发布日期；可选参数
                - **pages**: 最大请求次数，仅对请求账号喜欢页数据有效；可选参数
                - **cursor**: 可选参数
                - **count**: 可选参数
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_account(
            extract: Account, token: str = Depends(token_dependency)
        ):
            return await self.handle_account(extract, False)

        @self.server.post(
            "/douyin/mix",
            summary=_("获取合集作品数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **mix_id**: 抖音合集 ID
                - **detail_id**: 属于合集的抖音作品 ID
                - **cursor**: 可选参数
                - **count**: 可选参数
                
                **`mix_id` 和 `detail_id` 二选一，只需传入其中之一即可**
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_mix(extract: Mix, token: str = Depends(token_dependency)):
            is_mix, id_ = self.generate_mix_params(
                extract.mix_id,
                extract.detail_id,
            )
            if not isinstance(is_mix, bool):
                return DataResponse(
                    message=_("参数错误！"),
                    data=None,
                    params=extract.model_dump(),
                )
            if data := await self.deal_mix_detail(
                is_mix,
                id_,
                api=True,
                source=extract.source,
                cookie=extract.cookie,
                proxy=extract.proxy,
                cursor=extract.cursor,
                count=extract.count,
            ):
                return self.success_response(extract, data)
            return self.failed_response(extract)

        @self.server.post(
            "/douyin/live",
            summary=_("获取直播数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **web_rid**: 抖音直播 web_rid
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_live(extract: Live, token: str = Depends(token_dependency)):
            # if self.check_live_params(
            #     extract.web_rid,
            #     extract.room_id,
            #     extract.sec_user_id,
            # ):
            #     if data := await self.handle_live(
            #         extract,
            #     ):
            #         return self.success_response(extract, data[0])
            #     return self.failed_response(extract)
            # return DataResponse(
            #     message=_("参数错误！"),
            #     data=None,
            #     params=extract.model_dump(),
            # )
            if data := await self.handle_live(
                extract,
            ):
                return self.success_response(extract, data[0])
            return self.failed_response(extract)

        @self.server.post(
            "/douyin/comment",
            summary=_("获取作品评论数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **detail_id**: 抖音作品 ID；必需参数
                - **pages**: 最大请求次数；可选参数
                - **cursor**: 可选参数
                - **count**: 可选参数
                - **count_reply**: 可选参数
                - **reply**: 可选参数，默认值：False
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_comment(
            extract: Comment, token: str = Depends(token_dependency)
        ):
            if data := await self.comment_handle_single(
                extract.detail_id,
                cookie=extract.cookie,
                proxy=extract.proxy,
                source=extract.source,
                pages=extract.pages,
                cursor=extract.cursor,
                count=extract.count,
                count_reply=extract.count_reply,
                reply=extract.reply,
            ):
                return self.success_response(extract, data)
            return self.failed_response(extract)

        @self.server.post(
            "/douyin/reply",
            summary=_("获取评论回复数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **detail_id**: 抖音作品 ID；必需参数
                - **comment_id**: 评论 ID；必需参数
                - **pages**: 最大请求次数；可选参数
                - **cursor**: 可选参数
                - **count**: 可选参数
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_reply(extract: Reply, token: str = Depends(token_dependency)):
            if data := await self.reply_handle(
                extract.detail_id,
                extract.comment_id,
                cookie=extract.cookie,
                proxy=extract.proxy,
                pages=extract.pages,
                cursor=extract.cursor,
                count=extract.count,
                source=extract.source,
            ):
                return self.success_response(extract, data)
            return self.failed_response(extract)

        @self.server.post(
            "/douyin/search/general",
            summary=_("获取综合搜索数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **keyword**: 关键词；必需参数
                - **offset**: 起始页码；可选参数
                - **count**: 数据数量；可选参数
                - **pages**: 总页数；可选参数
                - **sort_type**: 排序依据；可选参数
                - **publish_time**: 发布时间；可选参数
                - **duration**: 视频时长；可选参数
                - **search_range**: 搜索范围；可选参数
                - **content_type**: 内容形式；可选参数
                
                **部分参数传入规则请查阅文档**: [参数含义](https://github.com/JoeanAmier/TikTokDownloader/wiki/Documentation#%E9%87%87%E9%9B%86%E6%90%9C%E7%B4%A2%E7%BB%93%E6%9E%9C%E6%95%B0%E6%8D%AE%E6%8A%96%E9%9F%B3)
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_search_general(
            extract: GeneralSearch, token: str = Depends(token_dependency)
        ):
            return await self.handle_search(extract)

        @self.server.post(
            "/douyin/search/video",
            summary=_("获取视频搜索数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **keyword**: 关键词；必需参数
                - **offset**: 起始页码；可选参数
                - **count**: 数据数量；可选参数
                - **pages**: 总页数；可选参数
                - **sort_type**: 排序依据；可选参数
                - **publish_time**: 发布时间；可选参数
                - **duration**: 视频时长；可选参数
                - **search_range**: 搜索范围；可选参数
                
                **部分参数传入规则请查阅文档**: [参数含义](https://github.com/JoeanAmier/TikTokDownloader/wiki/Documentation#%E9%87%87%E9%9B%86%E6%90%9C%E7%B4%A2%E7%BB%93%E6%9E%9C%E6%95%B0%E6%8D%AE%E6%8A%96%E9%9F%B3)
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_search_video(
            extract: VideoSearch, token: str = Depends(token_dependency)
        ):
            return await self.handle_search(extract)

        @self.server.post(
            "/douyin/search/user",
            summary=_("获取用户搜索数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **keyword**: 关键词；必需参数
                - **offset**: 起始页码；可选参数
                - **count**: 数据数量；可选参数
                - **pages**: 总页数；可选参数
                - **douyin_user_fans**: 粉丝数量；可选参数
                - **douyin_user_type**: 用户类型；可选参数
                
                **部分参数传入规则请查阅文档**: [参数含义](https://github.com/JoeanAmier/TikTokDownloader/wiki/Documentation#%E9%87%87%E9%9B%86%E6%90%9C%E7%B4%A2%E7%BB%93%E6%9E%9C%E6%95%B0%E6%8D%AE%E6%8A%96%E9%9F%B3)
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_search_user(
            extract: UserSearch, token: str = Depends(token_dependency)
        ):
            return await self.handle_search(extract)

        @self.server.post(
            "/douyin/search/live",
            summary=_("获取直播搜索数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **keyword**: 关键词；必需参数
                - **offset**: 起始页码；可选参数
                - **count**: 数据数量；可选参数
                - **pages**: 总页数；可选参数
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_search_live(
            extract: LiveSearch, token: str = Depends(token_dependency)
        ):
            return await self.handle_search(extract)

        @self.server.post(
            "/tiktok/share",
            summary=_("获取分享链接重定向的完整链接"),
            description=_(
                dedent("""
            **参数**:

            - **text**: 包含分享链接的字符串；必需参数
            - **proxy**: 代理；可选参数
            """)
            ),
            tags=["TikTok"],
            response_model=UrlResponse,
        )
        async def handle_share_tiktok(
            extract: ShortUrl, token: str = Depends(token_dependency)
        ):
            if url := await self.handle_redirect_tiktok(extract.text, extract.proxy):
                return UrlResponse(
                    message=_("请求链接成功！"),
                    url=url,
                    params=extract.model_dump(),
                )
            return UrlResponse(
                message=_("请求链接失败！"),
                url=None,
                params=extract.model_dump(),
            )

        @self.server.post(
            "/tiktok/download/share",
            summary=_("从分享链接解析并下载作品/图集/合辑"),
            description=_(
                dedent("""
                传入“分享文案/分享链接”，接口将自动判断是单作品还是合辑，并执行下载。

                下载完成后返回可访问的文件 URL（需要保持 API 服务运行）。
                """)
            ),
            tags=["TikTok"],
            response_model=DataResponse,
        )
        async def handle_download_share_tiktok(
            extract: DownloadFromShareTikTok,
            request: Request,
            token: str = Depends(token_dependency),
        ):
            resolved = await self.handle_redirect_tiktok(extract.text, extract.proxy)

            mix_flag, ids, titles = await self.links_tiktok.run(extract.text, "mix", extract.proxy)  # type: ignore[misc]
            if not ids:
                ids = await self.links_tiktok.run(extract.text, "detail", extract.proxy)  # type: ignore[assignment]
                mix_flag = False
                titles = []

            if not ids:
                return DataResponse(
                    message=_("解析分享链接失败！"),
                    data={"resolved_url": resolved, "items": []},
                    params=extract.model_dump(),
                )

            items_out = []
            if mix_flag:
                for idx, mix_id in enumerate(ids):
                    mix_title = titles[idx] if idx < len(titles) else ""
                    data = await self.deal_mix_detail(
                        True,
                        mix_id,
                        api=True,
                        source=False,
                        cookie=extract.cookie,
                        proxy=extract.proxy,
                        tiktok=True,
                        cursor=extract.cursor,
                        count=extract.count,
                        mix_title=mix_title,
                    )
                    if not data:
                        continue
                    root = self.downloader.storage_folder("mix", mix_id, extract.mark or mix_title)
                    await self.downloader.run_batch(
                        data,
                        True,
                        mode="mix",
                        mark=extract.mark,
                        mix_id=mix_id,
                        mix_title=mix_title,
                    )
                    for item in data:
                        files = self._predict_download_files(item, root)
                        items_out.append(
                            {
                                "id": item.get("id"),
                                "type": item.get("type"),
                                "files": [
                                    {"path": str(p.resolve()), "url": self._path_to_file_url(request, p)}
                                    for p in files
                                ],
                            }
                        )
            else:
                root, params, logger = self.record.run(self.parameter)
                async with logger(root, console=self.console, **params) as record:
                    data = await self._handle_detail(
                        ids,
                        True,
                        record,
                        api=True,
                        source=False,
                        cookie=extract.cookie,
                        proxy=extract.proxy,
                    )
                if data:
                    root = self.downloader.storage_folder("detail")
                    await self.downloader.run_general(data, True)
                    for item in data:
                        files = self._predict_download_files(item, root)
                        items_out.append(
                            {
                                "id": item.get("id"),
                                "type": item.get("type"),
                                "files": [
                                    {"path": str(p.resolve()), "url": self._path_to_file_url(request, p)}
                                    for p in files
                                ],
                            }
                        )

            data_payload = {
                "resolved_url": resolved,
                "mount": "/files",
                "root": str(self.parameter.root.resolve()),
                "items": items_out,
            }
            self._trigger_post_download_hook(
                {
                    "event": "download.completed",
                    "platform": "tiktok",
                    "source": "share",
                    "resolved_url": resolved,
                    "root": data_payload["root"],
                    "items": items_out,
                    "params": self._sanitize_hook_params(extract.model_dump()),
                }
            )
            return DataResponse(
                message=_("下载任务已完成！"),
                data=data_payload,
                params=extract.model_dump(),
            )

        @self.server.post(
            "/tiktok/download/favorite",
            summary=_("下载账号喜欢作品(TikTok)"),
            description=_(
                dedent("""
                下载指定账号的“喜欢”列表作品，并返回可访问文件 URL。
                
                - 传 sec_user_id：直接下载该账号喜欢列表
                - 或传 text：账号主页/分享链接（服务端会自动提取 sec_user_id）
                """)
            ),
            tags=["TikTok"],
            response_model=DataResponse,
        )
        async def handle_download_favorite_tiktok(
            extract: DownloadFavoriteTikTok,
            request: Request,
            token: str = Depends(token_dependency),
        ):
            sec_user_id = extract.sec_user_id
            resolved = ""
            if not sec_user_id:
                # 1) 允许用账号主页/分享链接自动提取
                if extract.text:
                    resolved = await self.handle_redirect_tiktok(extract.text, extract.proxy)
                    ids = await self.links_tiktok.run(extract.text, "user", extract.proxy)  # type: ignore[misc]
                    sec_user_id = ids[0] if ids else ""
                # 2) 不传 text / sec_user_id 时，默认使用 settings.json 的 owner_url_tiktok（视为“当前账号”）
                if not sec_user_id:
                    owner = (self.parameter.settings.read() or {}).get("owner_url_tiktok") or {}
                    sec_user_id = owner.get("sec_uid") or owner.get("secUid") or owner.get("sec_user_id") or ""
                    if not sec_user_id and owner.get("url"):
                        ids = await self.links_tiktok.run(owner["url"], "user", extract.proxy)  # type: ignore[misc]
                        sec_user_id = ids[0] if ids else ""

            if not sec_user_id:
                return DataResponse(
                    message=_(
                        "参数错误：缺少 sec_user_id！请传 sec_user_id 或 text；"
                        "或在 settings.json 设置 owner_url_tiktok.url / owner_url_tiktok.sec_uid 作为默认账号。"
                    ),
                    data={"resolved_url": resolved, "items": []},
                    params=extract.model_dump(),
                )

            info = await self.get_user_info_data(
                True,
                extract.cookie,
                extract.proxy,
                sec_user_id=sec_user_id,
            )
            if not info:
                return DataResponse(
                    message=_("获取账号信息失败，请检查 Cookie 登录状态！"),
                    data={"resolved_url": resolved, "items": []},
                    params=extract.model_dump(),
                )

            account_data, earliest, latest = await self._get_account_data_tiktok(
                cookie=extract.cookie,
                proxy=extract.proxy,
                sec_user_id=sec_user_id,
                tab="favorite",
                earliest=extract.earliest,
                latest=extract.latest,
                pages=extract.pages,
                cursor=extract.cursor,
                count=extract.count,
            )
            if not any(account_data):
                return DataResponse(
                    message=_("获取喜欢作品数据失败！"),
                    data={"resolved_url": resolved, "items": []},
                    params=extract.model_dump(),
                )

            data = await self._batch_process_detail(
                account_data,
                api=True,
                tiktok=True,
                info=info,
                mode="favorite",
                mark=extract.mark,
                user_id=sec_user_id,
                earliest=earliest,
                latest=latest,
            )
            if not data:
                return DataResponse(
                    message=_("提取作品数据失败！"),
                    data={"resolved_url": resolved, "items": []},
                    params=extract.model_dump(),
                )

            folder_name = extract.mark or info.get("nickname", "")
            root = self.downloader.storage_folder("favorite", sec_user_id, folder_name)
            await self.downloader.run_batch(
                data,
                True,
                mode="favorite",
                mark=extract.mark,
                user_id=sec_user_id,
                user_name=info.get("nickname", ""),
            )

            items_out = []
            for item in data:
                files = self._predict_download_files(item, root)
                items_out.append(
                    {
                        "id": item.get("id"),
                        "type": item.get("type"),
                        "files": [
                            {"path": str(p.resolve()), "url": self._path_to_file_url(request, p)}
                            for p in files
                        ],
                    }
                )

            data_payload = {
                "resolved_url": resolved,
                "mount": "/files",
                "root": str(self.parameter.root.resolve()),
                "earliest": str(earliest),
                "latest": str(latest),
                "items": items_out,
            }
            self._trigger_post_download_hook(
                {
                    "event": "download.completed",
                    "platform": "tiktok",
                    "source": "favorite",
                    "resolved_url": resolved,
                    "root": data_payload["root"],
                    "earliest": data_payload["earliest"],
                    "latest": data_payload["latest"],
                    "items": items_out,
                    "params": self._sanitize_hook_params(extract.model_dump()),
                }
            )
            return DataResponse(
                message=_("下载任务已完成！"),
                data=data_payload,
                params=extract.model_dump(),
            )

        @self.server.post(
            "/tiktok/detail",
            summary=_("获取单个作品数据"),
            description=_(
                dedent("""
                **参数**:

                - **cookie**: TikTok Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **detail_id**: TikTok 作品 ID；必需参数
                """)
            ),
            tags=["TikTok"],
            response_model=DataResponse,
        )
        async def handle_detail_tiktok(
            extract: DetailTikTok, token: str = Depends(token_dependency)
        ):
            return await self.handle_detail(extract, True)

        @self.server.post(
            "/tiktok/account",
            summary=_("获取账号作品数据"),
            description=_(
                dedent("""
                **参数**:

                - **cookie**: TikTok Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **sec_user_id**: TikTok 账号 secUid；必需参数
                - **tab**: 账号页面类型；可选参数，默认值：`post`
                - **earliest**: 作品最早发布日期；可选参数
                - **latest**: 作品最晚发布日期；可选参数
                - **pages**: 最大请求次数，仅对请求账号喜欢页数据有效；可选参数
                - **cursor**: 可选参数
                - **count**: 可选参数
                """)
            ),
            tags=["TikTok"],
            response_model=DataResponse,
        )
        async def handle_account_tiktok(
            extract: AccountTiktok, token: str = Depends(token_dependency)
        ):
            return await self.handle_account(extract, True)

        @self.server.post(
            "/tiktok/mix",
            summary=_("获取合辑作品数据"),
            description=_(
                dedent("""
                **参数**:

                - **cookie**: TikTok Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **mix_id**: TikTok 合集 ID；必需参数
                - **cursor**: 可选参数
                - **count**: 可选参数
                """)
            ),
            tags=["TikTok"],
            response_model=DataResponse,
        )
        async def handle_mix_tiktok(
            extract: MixTikTok, token: str = Depends(token_dependency)
        ):
            if data := await self.deal_mix_detail(
                True,
                extract.mix_id,
                api=True,
                source=extract.source,
                cookie=extract.cookie,
                proxy=extract.proxy,
                cursor=extract.cursor,
                count=extract.count,
            ):
                return self.success_response(extract, data)
            return self.failed_response(extract)

        @self.server.post(
            "/tiktok/live",
            summary=_("获取直播数据"),
            description=_(
                dedent("""
                **参数**:

                - **cookie**: TikTok Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **room_id**: TikTok 直播 room_id；必需参数
                """)
            ),
            tags=["TikTok"],
            response_model=DataResponse,
        )
        async def handle_live_tiktok(
            extract: Live, token: str = Depends(token_dependency)
        ):
            if data := await self.handle_live(
                extract,
                True,
            ):
                return self.success_response(extract, data[0])
            return self.failed_response(extract)

    async def handle_search(self, extract):
        if isinstance(
            data := await self.deal_search_data(
                extract,
                extract.source,
            ),
            list,
        ):
            return self.success_response(
                extract,
                *(data, None) if any(data) else (None, _("搜索结果为空！")),
            )
        return self.failed_response(extract)

    async def handle_detail(
        self,
        extract: Detail | DetailTikTok,
        tiktok=False,
    ):
        root, params, logger = self.record.run(self.parameter)
        async with logger(root, console=self.console, **params) as record:
            if data := await self._handle_detail(
                [extract.detail_id],
                tiktok,
                record,
                True,
                extract.source,
                extract.cookie,
                extract.proxy,
            ):
                return self.success_response(extract, data[0])
            return self.failed_response(extract)

    async def handle_account(
        self,
        extract: Account | AccountTiktok,
        tiktok=False,
    ):
        if data := await self.deal_account_detail(
            0,
            extract.sec_user_id,
            tab=extract.tab,
            earliest=extract.earliest,
            latest=extract.latest,
            pages=extract.pages,
            api=True,
            source=extract.source,
            cookie=extract.cookie,
            proxy=extract.proxy,
            tiktok=tiktok,
            cursor=extract.cursor,
            count=extract.count,
        ):
            return self.success_response(extract, data)
        return self.failed_response(extract)

    @staticmethod
    def success_response(
        extract,
        data: dict | list[dict],
        message: str = None,
    ):
        return DataResponse(
            message=message or _("获取数据成功！"),
            data=data,
            params=extract.model_dump(),
        )

    @staticmethod
    def failed_response(
        extract,
        message: str = None,
    ):
        return DataResponse(
            message=message or _("获取数据失败！"),
            data=None,
            params=extract.model_dump(),
        )

    @staticmethod
    def generate_mix_params(mix_id: str = None, detail_id: str = None):
        if mix_id:
            return True, mix_id
        return (False, detail_id) if detail_id else (None, None)

    @staticmethod
    def check_live_params(
        web_rid: str = None,
        room_id: str = None,
        sec_user_id: str = None,
    ) -> bool:
        return bool(web_rid or room_id and sec_user_id)

    async def handle_live(self, extract: Live | LiveTikTok, tiktok=False):
        if tiktok:
            data = await self.get_live_data_tiktok(
                extract.room_id,
                extract.cookie,
                extract.proxy,
            )
        else:
            data = await self.get_live_data(
                extract.web_rid,
                # extract.room_id,
                # extract.sec_user_id,
                cookie=extract.cookie,
                proxy=extract.proxy,
            )
        if extract.source:
            return [data]
        return await self.extractor.run(
            [data],
            None,
            "live",
            tiktok=tiktok,
        )
