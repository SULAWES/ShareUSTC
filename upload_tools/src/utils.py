"""工具函数模块

提供日志配置、文件类型检测、路径处理等通用工具函数。
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

import colorama
from colorama import Fore, Style

# 初始化 colorama
colorama.init()


# 支持的文件扩展名到资源类型的映射
RESOURCE_TYPE_MAP = {
    # 文档
    "pdf": "pdf",
    "md": "web_markdown",
    "markdown": "web_markdown",
    "ppt": "ppt",
    "pptx": "pptx",
    "doc": "doc",
    "docx": "docx",
    "txt": "txt",
    # 图片
    "jpg": "jpg",
    "jpeg": "jpeg",
    "png": "png",
    # 压缩包
    "zip": "zip",
}

# 资源分类枚举值
RESOURCE_CATEGORIES = {
    "exam_result": "考试成绩分布",
    "learning_note": "学习心得",
    "past_paper": "往年试卷",
    "note": "笔记",
    "review_outline": "复习提纲",
    "lecture": "讲义",
    "other": "其他",
}


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """配置日志系统
    
    Args:
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径，None 则只输出到控制台
        
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger("shareustc_upload")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除已有处理器
    logger.handlers.clear()
    
    # 控制台处理器 - 带颜色
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = ColoredFormatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了文件）
    if log_file:
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA + Style.BRIGHT,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # 保存原始 levelname
        original_levelname = record.levelname
        
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{Style.RESET_ALL}"
        
        result = super().format(record)
        
        # 恢复原始 levelname
        record.levelname = original_levelname
        return result


def print_banner():
    """打印程序横幅"""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
║                    ShareUSTC 批量上传工具                ║
║                         v0.1.0                           ║
╚══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)


def print_success(message: str):
    """打印成功消息"""
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")


def print_error(message: str):
    """打印错误消息"""
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}", file=sys.stderr)


def print_warning(message: str):
    """打印警告消息"""
    print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")


def print_info(message: str):
    """打印信息消息"""
    print(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")


def infer_resource_type(file_path: str) -> Tuple[str, str]:
    """根据文件路径推断资源类型和 MIME 类型
    
    Args:
        file_path: 文件路径
        
    Returns:
        (resource_type, mime_type) 元组
        
    Raises:
        ValueError: 不支持的文件类型
    """
    ext = Path(file_path).suffix.lower().lstrip(".")
    
    if ext not in RESOURCE_TYPE_MAP:
        supported = ", ".join(RESOURCE_TYPE_MAP.keys())
        raise ValueError(f"不支持的文件类型 '.{ext}'。支持的类型: {supported}")
    
    resource_type = RESOURCE_TYPE_MAP[ext]
    mime_type = _get_mime_type(resource_type)
    
    return resource_type, mime_type


def _get_mime_type(resource_type: str) -> str:
    """获取资源类型对应的 MIME 类型"""
    mime_map = {
        "pdf": "application/pdf",
        "web_markdown": "text/markdown",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "zip": "application/zip",
    }
    return mime_map.get(resource_type, "application/octet-stream")


def validate_category(category: str) -> str:
    """验证资源分类
    
    Args:
        category: 分类值
        
    Returns:
        标准化后的分类值
        
    Raises:
        ValueError: 无效的受控词
    """
    category = category.lower().strip()
    
    # 直接匹配
    if category in RESOURCE_CATEGORIES:
        return category
    
    # 常见别名映射
    aliases = {
        "exam": "exam_result",
        "result": "exam_result",
        "成绩": "exam_result",
        "learning": "learning_note",
        "心得": "learning_note",
        "paper": "past_paper",
        "试卷": "past_paper",
        "往年": "past_paper",
        "笔记": "note",
        "复习": "review_outline",
        "提纲": "review_outline",
        "outline": "review_outline",
        "讲义": "lecture",
        "课件": "lecture",
        "其他": "other",
    }
    
    if category in aliases:
        return aliases[category]
    
    valid = ", ".join(RESOURCE_CATEGORIES.keys())
    raise ValueError(f"无效的资源分类 '{category}'。有效的分类: {valid}")


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小
    
    Args:
        size_bytes: 字节数
        
    Returns:
        人类可读的文件大小字符串
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除不合法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # Windows 和 Unix 的非法字符
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    return filename


def get_timestamp() -> str:
    """获取当前时间戳字符串"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def expand_path(path: str) -> Path:
    """展开路径中的用户目录和变量
    
    注意: 相对路径（如 ./xxx 或 .shareustc/xxx）会保持相对路径形式，
    不会被转换为绝对路径，确保它们相对于当前工作目录。
    
    Args:
        path: 路径字符串
        
    Returns:
        展开后的 Path 对象
    """
    # 先展开环境变量
    expanded = os.path.expandvars(path)
    
    # 如果以 ~ 开头，展开为用户目录
    if expanded.startswith("~"):
        expanded = os.path.expanduser(expanded)
    
    return Path(expanded)


def resolve_path(path: str) -> Path:
    """解析路径为绝对路径
    
    如果路径是相对路径，则相对于当前工作目录解析为绝对路径。
    
    Args:
        path: 路径字符串
        
    Returns:
        绝对 Path 对象
    """
    path_obj = expand_path(path)
    if not path_obj.is_absolute():
        path_obj = Path.cwd() / path_obj
    return path_obj.resolve()


def ensure_dir(path: Path) -> Path:
    """确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        目录路径
    """
    # 如果是相对路径，基于当前工作目录解析
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path
