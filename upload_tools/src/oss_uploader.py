"""OSS 直传上传模块

实现与网页一致的 OSS 直传流程：
1. 获取 STS 临时凭证
2. 使用 STS 凭证直传文件到 OSS
3. 调用回调接口完成入库

参考前端实现：frontend/src/utils/oss-upload.ts 和 frontend/src/api/resource.ts
"""

import json
import logging
import time
import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass

import requests
from tqdm import tqdm

from csv_parser import UploadTask
from uploader import UploadResult
from utils import format_file_size

logger = logging.getLogger("shareustc_upload")


@dataclass
class OssStsToken:
    """OSS STS 临时凭证"""
    upload_mode: str  # 'sts' 或 'signed_url'
    upload_key: str
    expires_in: int
    storage_backend: str

    # STS 模式字段
    access_key_id: Optional[str] = None
    access_key_secret: Optional[str] = None
    security_token: Optional[str] = None
    expiration: Optional[str] = None
    bucket: Optional[str] = None
    region: Optional[str] = None
    endpoint: Optional[str] = None

    # Signed URL 模式字段
    upload_url: Optional[str] = None


class OssUploadError(Exception):
    """OSS 上传错误"""
    pass


class OssDirectUploader:
    """OSS 直传上传器

    实现与网页端一致的 OSS 直传流程。
    """

    # 分块大小：1MB
    CHUNK_SIZE = 1024 * 1024

    def __init__(
        self,
        base_url: str,
        session: requests.Session,
        timeout: int = 300,
        retry_count: int = 3,
        retry_delay: int = 2,
    ):
        """初始化 OSS 直传上传器

        Args:
            base_url: API 基础 URL
            session: HTTP Session（已包含认证 Cookie）
            timeout: 上传超时时间（秒）
            retry_count: 失败重试次数
            retry_delay: 重试间隔（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay

        logger.debug("OssDirectUploader 初始化:")
        logger.debug(f"  timeout: {timeout}")
        logger.debug(f"  retry_count: {retry_count}")

    def _get_sts_token(
        self,
        file_path: Path,
        mime_type: Optional[str] = None
    ) -> OssStsToken:
        """获取 STS 临时凭证

        Args:
            file_path: 文件路径
            mime_type: MIME 类型

        Returns:
            STS 凭证

        Raises:
            OssUploadError: 获取凭证失败
        """
        url = f"{self.base_url}/api/oss/sts-token"
        file_size = file_path.stat().st_size

        data = {
            "fileType": "resource",
            "fileName": file_path.name,
            "fileSize": file_size,
            "contentType": mime_type or "application/octet-stream",
        }

        logger.debug(f"获取 STS Token: {url}")
        logger.debug(f"请求数据: {data}")

        try:
            response = self.session.post(
                url,
                json=data,
                timeout=(10, 30),  # (连接超时, 读取超时)
            )
            response.raise_for_status()

            result = response.json()
            logger.debug(f"STS Token 响应: {result}")

            # 根据上传模式返回不同结构
            if result.get("uploadMode") == "sts":
                return OssStsToken(
                    upload_mode="sts",
                    upload_key=result["uploadKey"],
                    expires_in=result["expiresIn"],
                    storage_backend=result["storageBackend"],
                    access_key_id=result["accessKeyId"],
                    access_key_secret=result["accessKeySecret"],
                    security_token=result["securityToken"],
                    expiration=result["expiration"],
                    bucket=result["bucket"],
                    region=result["region"],
                    endpoint=result["endpoint"],
                )
            else:
                # signed_url 模式
                return OssStsToken(
                    upload_mode="signed_url",
                    upload_key=result["uploadKey"],
                    expires_in=result["expiresIn"],
                    storage_backend=result["storageBackend"],
                    upload_url=result["uploadUrl"],
                )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise OssUploadError("登录已过期，请重新登录")
            elif e.response.status_code == 400:
                error_msg = e.response.json().get("message", "请求参数错误")
                raise OssUploadError(f"获取上传凭证失败: {error_msg}")
            else:
                raise OssUploadError(f"获取上传凭证失败: HTTP {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            raise OssUploadError(f"获取上传凭证请求失败: {e}")

    def _upload_to_signed_url(
        self,
        token: OssStsToken,
        file_path: Path,
        mime_type: Optional[str],
        on_progress: Optional[Callable[[int], None]] = None
    ) -> None:
        """使用预签名 URL 上传文件

        Args:
            token: STS 凭证（signed_url 模式）
            file_path: 文件路径
            mime_type: MIME 类型
            on_progress: 进度回调函数

        Raises:
            OssUploadError: 上传失败
        """
        if not token.upload_url:
            raise OssUploadError("预签名 URL 为空")

        file_size = file_path.stat().st_size
        headers = {}
        if mime_type:
            headers["Content-Type"] = mime_type

        logger.debug(f"使用预签名 URL 上传: {file_path}")
        logger.debug(f"URL: {token.upload_url[:100]}...")

        try:
            with open(file_path, "rb") as f:
                # 创建带进度追踪的读取器
                if on_progress:
                    def chunked_reader():
                        uploaded = 0
                        while True:
                            chunk = f.read(self.CHUNK_SIZE)
                            if not chunk:
                                break
                            uploaded += len(chunk)
                            progress = int((uploaded / file_size) * 100)
                            on_progress(progress)
                            yield chunk

                    response = self.session.put(
                        token.upload_url,
                        data=chunked_reader(),
                        headers=headers,
                        timeout=(30, self.timeout),
                    )
                else:
                    response = self.session.put(
                        token.upload_url,
                        data=f,
                        headers=headers,
                        timeout=(30, self.timeout),
                    )

            response.raise_for_status()
            logger.debug("预签名 URL 上传成功")

        except requests.exceptions.RequestException as e:
            raise OssUploadError(f"上传到 OSS 失败: {e}")

    def _upload_with_sts(
        self,
        token: OssStsToken,
        file_path: Path,
        mime_type: Optional[str],
        on_progress: Optional[Callable[[int], None]] = None
    ) -> None:
        """使用 STS 临时凭证上传文件到 OSS

        实现 OSS4-HMAC-SHA256 签名算法，与前端保持一致。

        Args:
            token: STS 凭证（sts 模式）
            file_path: 文件路径
            mime_type: MIME 类型
            on_progress: 进度回调函数

        Raises:
            OssUploadError: 上传失败
        """
        if not all([token.endpoint, token.bucket, token.region,
                    token.access_key_id, token.access_key_secret, token.security_token]):
            raise OssUploadError("STS 凭证不完整")

        # 规范化参数
        normalized_key = token.upload_key.lstrip("/")
        endpoint = token.endpoint.strip()

        # 移除 endpoint 的协议前缀
        if endpoint.startswith("http://"):
            endpoint_host = endpoint[7:].rstrip("/")
            scheme = "http"
        elif endpoint.startswith("https://"):
            endpoint_host = endpoint[8:].rstrip("/")
            scheme = "https"
        else:
            endpoint_host = endpoint.rstrip("/")
            scheme = "https"

        # 构建对象 URL 主机名
        if endpoint_host.startswith(f"{token.bucket}."):
            object_host = endpoint_host
        else:
            object_host = f"{token.bucket}.{endpoint_host}"

        # 构建对象 URL
        object_url = f"{scheme}://{object_host}/{normalized_key}"

        # 构建签名
        headers = self._build_oss_headers(
            token=token,
            host=object_host,
            bucket=token.bucket,
            key=normalized_key,
        )

        file_size = file_path.stat().st_size
        logger.debug(f"使用 STS 上传: {file_path}")
        logger.debug(f"URL: {object_url}")

        try:
            with open(file_path, "rb") as f:
                # 创建带进度追踪的读取器
                if on_progress:
                    def chunked_reader():
                        uploaded = 0
                        while True:
                            chunk = f.read(self.CHUNK_SIZE)
                            if not chunk:
                                break
                            uploaded += len(chunk)
                            progress = int((uploaded / file_size) * 100)
                            on_progress(progress)
                            yield chunk

                    response = requests.put(
                        object_url,
                        data=chunked_reader(),
                        headers=headers,
                        timeout=(30, self.timeout),
                    )
                else:
                    response = requests.put(
                        object_url,
                        data=f,
                        headers=headers,
                        timeout=(30, self.timeout),
                    )

            if response.status_code >= 400:
                request_id = response.headers.get("x-oss-request-id")
                error_msg = response.text[:500] if response.text else "未知错误"
                req_id_info = f" [request-id: {request_id}]" if request_id else ""
                raise OssUploadError(f"OSS 上传失败: HTTP {response.status_code}{req_id_info} - {error_msg}")

            logger.debug("STS 上传成功")

        except requests.exceptions.RequestException as e:
            raise OssUploadError(f"上传到 OSS 失败: {e}")

    def _build_oss_headers(
        self,
        token: OssStsToken,
        host: str,
        bucket: str,
        key: str,
    ) -> Dict[str, str]:
        """构建 OSS 请求头（包含签名）

        实现 OSS4-HMAC-SHA256 签名算法。

        Args:
            token: STS 凭证
            host: 主机名
            bucket: Bucket 名称
            key: 对象 Key

        Returns:
            请求头字典
        """
        # 获取当前 UTC 时间
        now = datetime.now(timezone.utc)
        short_date = now.strftime("%Y%m%d")
        full_date = now.strftime("%Y%m%dT%H%M%SZ")

        # 规范化 URI
        canonical_uri = f"/{bucket}/{key}"

        # 构建规范请求头
        payload_hash = "UNSIGNED-PAYLOAD"
        signed_headers_list = [
            ("host", host),
            ("x-oss-content-sha256", payload_hash),
            ("x-oss-date", full_date),
            ("x-oss-security-token", token.security_token),
        ]
        signed_headers_list.sort(key=lambda x: x[0])

        canonical_headers = "".join(f"{k}:{v}\n" for k, v in signed_headers_list)
        additional_headers = "host"

        # 构建规范请求
        canonical_request = (
            f"PUT\n"
            f"{canonical_uri}\n"
            f"\n"  # 查询字符串为空
            f"{canonical_headers}\n"
            f"{additional_headers}\n"
            f"{payload_hash}"
        )

        # 构建待签名字符串
        credential_scope = f"{short_date}/{token.region}/oss/aliyun_v4_request"
        hashed_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = (
            f"OSS4-HMAC-SHA256\n"
            f"{full_date}\n"
            f"{credential_scope}\n"
            f"{hashed_request}"
        )

        # 派生签名密钥
        signing_key = self._derive_signing_key(
            token.access_key_secret,
            short_date,
            token.region,
        )

        # 计算签名
        signature = hmac.new(
            signing_key,
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # 构建 Authorization 头
        authorization = (
            f"OSS4-HMAC-SHA256 "
            f"Credential={token.access_key_id}/{credential_scope},"
            f"AdditionalHeaders={additional_headers},"
            f"Signature={signature}"
        )

        return {
            "Authorization": authorization,
            "x-oss-date": full_date,
            "x-oss-content-sha256": payload_hash,
            "x-oss-security-token": token.security_token,
            "Host": host,
        }

    def _derive_signing_key(
        self,
        access_key_secret: str,
        short_date: str,
        region: str,
    ) -> bytes:
        """派生签名密钥

        Args:
            access_key_secret: Access Key Secret
            short_date: 短日期格式（YYYYMMDD）
            region: 区域

        Returns:
            签名密钥
        """
        # 第一步：使用 aliyun_v4{access_key_secret} 作为初始密钥
        date_key = hmac.new(
            f"aliyun_v4{access_key_secret}".encode("utf-8"),
            short_date.encode("utf-8"),
            hashlib.sha256
        ).digest()

        # 第二步：使用区域
        region_key = hmac.new(
            date_key,
            region.encode("utf-8"),
            hashlib.sha256
        ).digest()

        # 第三步：使用服务名（oss）
        service_key = hmac.new(
            region_key,
            b"oss",
            hashlib.sha256
        ).digest()

        # 第四步：使用 aliyun_v4_request
        signing_key = hmac.new(
            service_key,
            b"aliyun_v4_request",
            hashlib.sha256
        ).digest()

        return signing_key

    def _callback_upload(
        self,
        token: OssStsToken,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """调用回调接口完成资源入库

        Args:
            token: STS 凭证（包含 upload_key）
            metadata: 资源元数据

        Returns:
            回调响应

        Raises:
            OssUploadError: 回调失败
        """
        url = f"{self.base_url}/api/oss/callback/resource"

        # 构建回调请求数据
        callback_data = {
            **metadata,
            "ossKey": token.upload_key,
        }

        logger.debug(f"调用回调接口: {url}")
        logger.debug(f"回调数据: {callback_data}")

        try:
            response = self.session.post(
                url,
                json=callback_data,
                timeout=(10, 30),
            )
            response.raise_for_status()

            result = response.json()
            logger.debug(f"回调响应: {result}")
            return result

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise OssUploadError("登录已过期，请重新登录")
            else:
                error_msg = e.response.json().get("message", f"HTTP {e.response.status_code}")
                raise OssUploadError(f"资源入库失败: {error_msg}")
        except requests.exceptions.RequestException as e:
            raise OssUploadError(f"回调请求失败: {e}")

    def upload_single(
        self,
        task: UploadTask,
        progress_bar: Optional[tqdm] = None,
    ) -> UploadResult:
        """上传单个文件（OSS 直传方式）

        完整流程：
        1. 获取 STS 临时凭证
        2. 直传文件到 OSS
        3. 调用回调接口完成入库

        Args:
            task: 上传任务
            progress_bar: 可选的 tqdm 进度条对象

        Returns:
            上传结果
        """
        start_time = time.time()
        file_size = task.file_path.stat().st_size
        size_str = format_file_size(file_size)

        logger.info(f"[OSS直传] {task.title} ({size_str})")

        # 检查文件是否存在
        if not task.file_path.exists():
            return UploadResult(
                success=False,
                task=task,
                error=f"文件不存在: {task.file_path}",
                duration=time.time() - start_time,
            )

        # 构建元数据
        metadata = {
            "title": task.title,
            "courseName": task.course_name,
            "resourceType": task.resource_type,
            "category": task.category,
            "tags": task.tags,
            "description": task.description,
            "teacherSns": task.matched_teacher_sns,
            "courseSns": task.matched_course_sns,
        }

        # 执行上传（带重试）
        for attempt in range(self.retry_count + 1):
            if attempt > 0:
                logger.info(f"第 {attempt}/{self.retry_count} 次重试...")
                time.sleep(self.retry_delay * attempt)

            try:
                # 1. 获取 STS Token
                logger.debug("获取 STS Token...")
                token = self._get_sts_token(task.file_path, task.mime_type)

                # 2. 上传文件到 OSS
                logger.debug(f"上传文件到 OSS (mode={token.upload_mode})...")

                # 创建进度回调
                if progress_bar:
                    def on_progress(percent: int):
                        progress_bar.n = int(file_size * percent / 100)
                        progress_bar.refresh()
                else:
                    on_progress = None

                if token.upload_mode == "sts":
                    self._upload_with_sts(token, task.file_path, task.mime_type, on_progress)
                else:
                    self._upload_to_signed_url(token, task.file_path, task.mime_type, on_progress)

                # 3. 调用回调接口
                logger.debug("调用回调接口...")
                result = self._callback_upload(token, metadata)

                duration = time.time() - start_time
                return UploadResult(
                    success=True,
                    task=task,
                    resource_id=result.get("id"),
                    message="上传成功",
                    duration=duration,
                )

            except OssUploadError as e:
                logger.error(f"OSS 上传错误: {e}")
                if attempt == self.retry_count:
                    duration = time.time() - start_time
                    return UploadResult(
                        success=False,
                        task=task,
                        error=str(e),
                        duration=duration,
                    )

            except Exception as e:
                logger.error(f"上传时发生错误: {e}")
                if attempt == self.retry_count:
                    duration = time.time() - start_time
                    return UploadResult(
                        success=False,
                        task=task,
                        error=f"上传失败: {str(e)}",
                        duration=duration,
                    )

        # 所有重试都失败
        duration = time.time() - start_time
        return UploadResult(
            success=False,
            task=task,
            error="上传失败，已达到最大重试次数",
            duration=duration,
        )
