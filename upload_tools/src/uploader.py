"""上传核心模块

执行实际的文件上传操作，包括重试、断点续传等功能。
"""

import json
import logging
import time
import os
import socket
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime

import requests
from tqdm import tqdm
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from csv_parser import UploadTask
from utils import format_file_size, get_timestamp

logger = logging.getLogger("shareustc_upload")


@dataclass
class UploadResult:
    """单个上传结果"""
    success: bool
    task: UploadTask
    resource_id: Optional[str] = None
    message: str = ""
    error: Optional[str] = None
    timestamp: str = ""
    duration: float = 0.0  # 上传耗时（秒）
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "title": self.task.title,
            "file_path": str(self.task.file_path),
            "row_number": self.task.row_number,
            "resource_id": self.resource_id,
            "message": self.message,
            "error": self.error,
            "timestamp": self.timestamp,
            "duration": self.duration,
        }


class UploadError(Exception):
    """上传错误"""
    pass


class ProgressFileWrapper:
    """带进度追踪的文件包装器
    
    包装文件对象，在读取数据时更新进度条。
    """
    
    def __init__(self, filepath: Path, progress_bar: tqdm):
        self.filepath = filepath
        self.fileobj = open(filepath, 'rb')
        self.progress_bar = progress_bar
        self.read_size = 0
        
    def read(self, size: int = -1) -> bytes:
        data = self.fileobj.read(size)
        self.read_size += len(data)
        self.progress_bar.update(len(data))
        return data
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fileobj.close()
    
    def __getattr__(self, name):
        """委托其他属性到文件对象"""
        return getattr(self.fileobj, name)


class BatchUploader:
    """批量上传器"""

    # 大文件阈值：10MB 以上使用流式上传并显示进度
    LARGE_FILE_THRESHOLD = 10 * 1024 * 1024

    # 分块大小：1MB
    CHUNK_SIZE = 1024 * 1024

    # 大文件上传的最小速度（MB/s），用于计算超时时间
    MIN_UPLOAD_SPEED = 1 * 1024 * 1024  # 1 MB/s

    # 大文件上传的最小超时时间（秒）
    MIN_LARGE_FILE_TIMEOUT = 180  # 3 分钟

    # 大文件上传的最大超时时间（秒）
    MAX_LARGE_FILE_TIMEOUT = 3600  # 1 小时
    
    def __init__(
        self,
        base_url: str,
        session: requests.Session,
        timeout: int = 300,
        retry_count: int = 3,
        retry_delay: int = 2,
    ):
        """初始化批量上传器
        
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
        
        logger.debug("BatchUploader 初始化:")
        logger.debug(f"  timeout: {timeout}")
        logger.debug(f"  retry_count: {retry_count}")
        logger.debug(f"  retry_delay: {retry_delay}")
    
    def upload(
        self,
        tasks: List[UploadTask],
        progress_callback=None,
    ) -> List[UploadResult]:
        """批量上传
        
        Args:
            tasks: 上传任务列表
            progress_callback: 进度回调函数 (current, total, task)
            
        Returns:
            上传结果列表
        """
        total = len(tasks)
        results = []
        
        logger.info(f"开始批量上传，共 {total} 个任务")
        
        for i, task in enumerate(tasks, 1):
            file_size = task.file_path.stat().st_size
            size_str = format_file_size(file_size)
            
            logger.info(f"[{i}/{total}] 正在上传: {task.title} ({size_str})")
            
            # 执行上传
            result = self.upload_single(task)
            results.append(result)

            # 进度回调（上传完成后更新）
            if progress_callback:
                progress_callback(i, total, task)
            
            # 根据结果记录日志
            if result.success:
                logger.info(
                    f"✓ 上传成功: {task.title} -> ID: {result.resource_id} "
                    f"({result.duration:.2f}s)"
                )
            else:
                logger.error(f"✗ 上传失败: {task.title} - {result.error}")
            
            # 短暂延迟，避免请求过快
            if i < total:
                time.sleep(0.5)
        
        # 统计
        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"批量上传完成: 成功 {success_count}/{total}, "
            f"失败 {total - success_count}/{total}"
        )
        
        return results
    
    def upload_single(self, task: UploadTask) -> UploadResult:
        """上传单个文件

        Args:
            task: 上传任务

        Returns:
            上传结果
        """
        start_time = time.time()

        # 检查文件是否存在（上传前再次验证，防止文件被删除或修改）
        if not task.file_path.exists():
            return UploadResult(
                success=False,
                task=task,
                error=f"文件不存在: {task.file_path}",
                duration=time.time() - start_time,
            )

        # 检查文件是否可读
        if not task.file_path.is_file():
            return UploadResult(
                success=False,
                task=task,
                error=f"路径不是文件或无法访问: {task.file_path}",
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
        
        logger.debug("上传元数据:")
        for key, value in metadata.items():
            logger.debug(f"  {key}: {value}")
        
        # 执行上传（带重试）
        for attempt in range(self.retry_count + 1):
            if attempt > 0:
                logger.info(f"第 {attempt}/{self.retry_count} 次重试...")
                time.sleep(self.retry_delay * attempt)  # 指数退避
            
            try:
                result = self._do_upload(task, metadata, start_time)
                if result.success:
                    return result
                    
            except requests.exceptions.Timeout as e:
                logger.warning(f"上传超时: {e}")
                if attempt == self.retry_count:
                    return UploadResult(
                        success=False,
                        task=task,
                        error=f"上传超时（{self.timeout}秒），已重试 {self.retry_count} 次。建议：1) 检查网络连接 2) 对于大文件请确保网络稳定 3) 可尝试增加超时时间",
                        duration=time.time() - start_time,
                    )
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"连接错误: {e}")
                if attempt == self.retry_count:
                    return UploadResult(
                        success=False,
                        task=task,
                        error=f"连接失败，已重试 {self.retry_count} 次: {e}",
                        duration=time.time() - start_time,
                    )
                    
            except Exception as e:
                logger.error(f"上传时发生错误: {e}")
                if attempt == self.retry_count:
                    return UploadResult(
                        success=False,
                        task=task,
                        error=f"上传失败: {str(e)}",
                        duration=time.time() - start_time,
                    )
        
        # 所有重试都失败
        return UploadResult(
            success=False,
            task=task,
            error="上传失败，已达到最大重试次数",
            duration=time.time() - start_time,
        )
    
    def _do_upload(self, task: UploadTask, metadata: Dict[str, Any], start_time: float) -> UploadResult:
        """执行实际上传

        对于大文件使用流式上传并显示进度条。

        Args:
            task: 上传任务
            metadata: 资源元数据
            start_time: 开始时间戳（用于计算耗时）

        Returns:
            上传结果
        """
        url = f"{self.base_url}/api/resources"
        file_size = task.file_path.stat().st_size

        logger.debug(f"POST {url}")
        logger.debug(f"文件: {task.file_path} ({format_file_size(file_size)})")

        # 判断是否为超大文件
        is_large_file = file_size > self.LARGE_FILE_THRESHOLD

        if is_large_file:
            # 大文件使用流式上传并显示进度
            return self._upload_large_file(url, task, metadata, file_size, start_time)
        else:
            # 小文件直接上传
            return self._upload_small_file(url, task, metadata, start_time)
    
    def _upload_small_file(self, url: str, task: UploadTask, metadata: Dict, start_time: float) -> UploadResult:
        """上传小文件（直接上传）

        Args:
            url: 上传URL
            task: 上传任务
            metadata: 资源元数据
            start_time: 开始时间戳（用于计算耗时）

        Returns:
            上传结果
        """
        data = {
            "metadata": json.dumps(metadata, ensure_ascii=False),
        }

        with open(task.file_path, "rb") as f:
            files = {
                "file": (task.file_path.name, f, task.mime_type or "application/octet-stream"),
            }

            # 使用分离的超时设置：连接超时10秒，读取使用配置的超时
            response = self.session.post(
                url,
                data=data,
                files=files,
                timeout=(10, self.timeout),  # (连接超时, 读取超时)
            )

        duration = time.time() - start_time
        return self._handle_response(response, task, duration)
    
    def _upload_large_file(self, url: str, task: UploadTask, metadata: Dict, file_size: int, start_time: float) -> UploadResult:
        """上传大文件（真正的流式上传+进度条）

        使用 requests_toolbelt.MultipartEncoder 实现真正的流式 multipart 上传，
        避免内存缓冲问题。

        Args:
            url: 上传URL
            task: 上传任务
            metadata: 资源元数据
            file_size: 文件大小（字节）
            start_time: 开始时间戳（用于计算耗时）

        Returns:
            上传结果
        """
        from utils import print_info

        print_info(f"大文件检测（{format_file_size(file_size)}），使用流式上传...")

        file_handle = None
        progress_bar = None

        try:
            # 打开文件
            file_handle = open(task.file_path, 'rb')

            # 创建进度条
            progress_bar = tqdm(
                total=file_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=f"上传 {task.file_path.name[:20]}",
                ncols=80,
            )

            # 回调函数：更新进度条
            def callback(monitor):
                progress_bar.n = monitor.bytes_read
                progress_bar.refresh()

            # 创建 MultipartEncoder 实现真正的流式上传
            encoder = MultipartEncoder({
                'metadata': json.dumps(metadata, ensure_ascii=False),
                'file': (task.file_path.name, file_handle, task.mime_type or "application/octet-stream"),
            })

            # 包装 encoder 以追踪进度
            monitor = MultipartEncoderMonitor(encoder, callback)

            # 计算超时时间
            # 根据文件大小和最小上传速度计算，留出3倍余量
            estimated_time = file_size / self.MIN_UPLOAD_SPEED
            actual_timeout = max(self.MIN_LARGE_FILE_TIMEOUT, estimated_time * 3)
            actual_timeout = min(actual_timeout, self.MAX_LARGE_FILE_TIMEOUT)

            logger.debug(f"大文件上传超时设置: {actual_timeout:.0f}秒")

            # 设置请求头
            headers = {
                'Content-Type': monitor.content_type,
            }

            # 发送请求 - 使用 data=monitor 实现流式上传
            response = self.session.post(
                url,
                data=monitor,  # MultipartEncoderMonitor 作为迭代器
                headers=headers,
                timeout=(30, actual_timeout),  # (连接超时30s, 读取超时动态计算)
            )

            duration = time.time() - start_time
            return self._handle_response(response, task, duration)

        except Exception:
            raise
        finally:
            # 确保资源被释放
            if file_handle is not None:
                file_handle.close()
            if progress_bar is not None:
                progress_bar.close()
    
    def _handle_response(self, response: requests.Response, task: UploadTask, duration: float) -> UploadResult:
        """处理上传响应

        Args:
            response: HTTP 响应
            task: 上传任务
            duration: 上传耗时（秒）

        Returns:
            上传结果
        """
        logger.debug(f"响应状态码: {response.status_code}")
        logger.debug(f"响应内容: {response.text[:500]}")

        # 处理响应
        if response.status_code == 201:
            # 上传成功
            data = response.json()
            return UploadResult(
                success=True,
                task=task,
                resource_id=data.get("id"),
                message="上传成功",
                duration=duration,
            )

        elif response.status_code == 400:
            # 请求参数错误
            try:
                error_msg = response.json().get("message", "请求参数错误")
            except:
                error_msg = "请求参数错误"
            return UploadResult(
                success=False,
                task=task,
                error=f"参数错误: {error_msg}",
                duration=duration,
            )

        elif response.status_code == 401:
            # 未认证
            return UploadResult(
                success=False,
                task=task,
                error="登录已过期，请重新登录",
                duration=duration,
            )

        elif response.status_code == 413:
            # 文件过大
            return UploadResult(
                success=False,
                task=task,
                error="文件过大，超过服务器限制",
                duration=duration,
            )

        else:
            # 其他错误
            try:
                error_msg = response.json().get("message", f"服务器错误: {response.status_code}")
            except:
                error_msg = f"服务器错误: {response.status_code}"

            return UploadResult(
                success=False,
                task=task,
                error=error_msg,
                duration=duration,
            )


class Checkpoint:
    """断点续传检查点"""
    
    def __init__(self, checkpoint_file: str):
        """初始化检查点
        
        Args:
            checkpoint_file: 检查点文件路径
        """
        self.checkpoint_file = Path(checkpoint_file)
        self.completed_indices: set = set()
        self.failed_tasks: List[Dict] = []
        self.csv_path: Optional[str] = None
        
        logger.debug(f"Checkpoint 初始化，文件: {checkpoint_file}")
    
    def load(self) -> bool:
        """加载检查点
        
        Returns:
            是否成功加载
        """
        if not self.checkpoint_file.exists():
            logger.debug("检查点文件不存在")
            return False
        
        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.completed_indices = set(data.get("completed", []))
            self.failed_tasks = data.get("failed", [])
            self.csv_path = data.get("csv_path")
            
            logger.info(
                f"已加载检查点: 已完成 {len(self.completed_indices)} 个, "
                f"失败 {len(self.failed_tasks)} 个"
            )
            return True
            
        except Exception as e:
            logger.warning(f"加载检查点失败: {e}")
            return False
    
    def save(self, csv_path: str):
        """保存检查点
        
        Args:
            csv_path: CSV 文件路径
        """
        data = {
            "timestamp": datetime.now().isoformat(),
            "csv_path": csv_path,
            "completed": list(self.completed_indices),
            "failed": self.failed_tasks,
        }
        
        try:
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"检查点已保存: {self.checkpoint_file}")
            
        except Exception as e:
            logger.warning(f"保存检查点失败: {e}")
    
    def mark_completed(self, index: int):
        """标记任务已完成
        
        Args:
            index: 任务索引
        """
        self.completed_indices.add(index)
    
    def mark_failed(self, index: int, task: UploadTask, error: str):
        """标记任务失败
        
        Args:
            index: 任务索引
            task: 上传任务
            error: 错误信息
        """
        self.failed_tasks.append({
            "index": index,
            "task": task.to_dict(),
            "error": error,
        })
    
    def is_completed(self, index: int) -> bool:
        """检查任务是否已完成
        
        Args:
            index: 任务索引
            
        Returns:
            是否已完成
        """
        return index in self.completed_indices
    
    def clear(self):
        """清除检查点"""
        self.completed_indices.clear()
        self.failed_tasks.clear()
        self.csv_path = None
        
        if self.checkpoint_file.exists():
            try:
                self.checkpoint_file.unlink()
                logger.debug(f"已删除检查点文件: {self.checkpoint_file}")
            except Exception as e:
                logger.warning(f"删除检查点文件失败: {e}")
    
    def get_remaining_tasks(self, all_tasks: List[UploadTask]) -> List[UploadTask]:
        """获取剩余未完成的任务
        
        Args:
            all_tasks: 所有任务
            
        Returns:
            未完成的任务列表
        """
        remaining = []
        for i, task in enumerate(all_tasks):
            if not self.is_completed(i):
                remaining.append(task)
        
        return remaining


def resume_upload(
    checkpoint: Checkpoint,
    all_tasks: List[UploadTask],
    uploader: BatchUploader,
) -> List[UploadResult]:
    """从检查点恢复上传
    
    Args:
        checkpoint: 检查点
        all_tasks: 所有任务
        uploader: 上传器
        
    Returns:
        上传结果列表（包含已完成的）
    """
    total = len(all_tasks)
    results = []
    
    logger.info(f"恢复上传，总计 {total} 个任务，已完成 {len(checkpoint.completed_indices)} 个")
    
    for i, task in enumerate(all_tasks):
        if checkpoint.is_completed(i):
            # 已完成，创建成功结果
            result = UploadResult(
                success=True,
                task=task,
                message="从检查点恢复",
            )
            results.append(result)
            logger.debug(f"任务 {i} 已从检查点恢复")
        else:
            # 需要上传
            result = uploader.upload_single(task)
            results.append(result)
            
            # 更新检查点
            if result.success:
                checkpoint.mark_completed(i)
            else:
                checkpoint.mark_failed(i, task, result.error or "未知错误")
            
            checkpoint.save(checkpoint.csv_path or "")
    
    return results
