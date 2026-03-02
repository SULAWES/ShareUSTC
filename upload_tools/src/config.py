"""配置管理模块

管理工具的配置，支持 YAML 配置文件和环境变量。
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict

import yaml

from utils import expand_path, ensure_dir, resolve_path

logger = logging.getLogger("shareustc_upload")


@dataclass
class ServerConfig:
    """服务器配置"""
    base_url: str = ""
    timeout: int = 300
    retry_count: int = 3
    retry_delay: int = 2


@dataclass
class UploadConfig:
    """上传配置"""
    chunk_size: int = 8192
    max_file_size: int = 104857600  # 100MB
    checkpoint_file: str = ".upload_checkpoint"


@dataclass
class OutputConfig:
    """输出配置"""
    report_format: str = "csv"
    verbose: bool = False
    log_level: str = "INFO"


@dataclass
class CacheConfig:
    """缓存配置"""
    entity_cache_ttl: int = 3600


@dataclass
class PathConfig:
    """路径配置 - 默认使用当前目录下的 .shareustc/ 文件夹"""
    cookie_file: str = ".shareustc/cookies.json"
    log_file: str = ".shareustc/upload.log"


@dataclass
class Config:
    """完整配置"""
    server: ServerConfig = field(default_factory=ServerConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    
    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """从 YAML 文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            Config 实例
        """
        config_path = expand_path(config_path)
        logger.debug(f"从文件加载配置: {config_path}")

        if not config_path.exists():
            logger.debug(f"配置文件不存在: {config_path}")
            return cls()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            logger.debug(f"配置文件内容: {data}")
        except Exception as e:
            logger.error(f"读取配置文件失败: {e}")
            return cls()

        return cls.from_dict(data)
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置
        
        支持的环境变量:
        - SHAREUSTC_SERVER: 服务器地址
        - SHAREUSTC_TIMEOUT: 超时时间
        - SHAREUSTC_RETRY_COUNT: 重试次数
        - SHAREUSTC_LOG_LEVEL: 日志级别
        
        Returns:
            Config 实例
        """
        logger.debug("从环境变量加载配置")
        
        config = cls()
        
        # 服务器配置
        if server := os.getenv("SHAREUSTC_SERVER"):
            config.server.base_url = server
            logger.debug(f"从环境变量设置服务器地址: {server}")
        
        if timeout := os.getenv("SHAREUSTC_TIMEOUT"):
            try:
                config.server.timeout = int(timeout)
                logger.debug(f"从环境变量设置超时时间: {timeout}")
            except ValueError:
                logger.warning(f"无效的超时时间值: {timeout}")
        
        if retry_count := os.getenv("SHAREUSTC_RETRY_COUNT"):
            try:
                config.server.retry_count = int(retry_count)
                logger.debug(f"从环境变量设置重试次数: {retry_count}")
            except ValueError:
                logger.warning(f"无效的重试次数值: {retry_count}")
        
        # 输出配置
        if log_level := os.getenv("SHAREUSTC_LOG_LEVEL"):
            config.output.log_level = log_level
            logger.debug(f"从环境变量设置日志级别: {log_level}")
        
        return config
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """从字典创建配置
        
        Args:
            data: 配置字典
            
        Returns:
            Config 实例
        """
        config = cls()
        
        if "server" in data:
            config.server = ServerConfig(**data["server"])
        if "upload" in data:
            config.upload = UploadConfig(**data["upload"])
        if "output" in data:
            config.output = OutputConfig(**data["output"])
        if "cache" in data:
            config.cache = CacheConfig(**data["cache"])
        if "paths" in data:
            config.paths = PathConfig(**data["paths"])
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            配置字典
        """
        return {
            "server": asdict(self.server),
            "upload": asdict(self.upload),
            "output": asdict(self.output),
            "cache": asdict(self.cache),
            "paths": asdict(self.paths),
        }
    
    def save(self, config_path: str):
        """保存配置到 YAML 文件
        
        Args:
            config_path: 配置文件路径
        """
        config_path = expand_path(config_path)
        ensure_dir(config_path.parent)
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"配置已保存到: {config_path}")
    
    def get_cookie_path(self) -> Path:
        """获取 Cookie 文件路径
        
        路径基于当前工作目录解析。
        
        Returns:
            Cookie 文件路径（绝对路径）
        """
        path = resolve_path(self.paths.cookie_file)
        ensure_dir(path.parent)
        return path
    
    def get_log_path(self) -> Optional[Path]:
        """获取日志文件路径
        
        路径基于当前工作目录解析。
        
        Returns:
            日志文件路径（绝对路径），如果未配置则返回 None
        """
        if not self.paths.log_file:
            return None
        path = resolve_path(self.paths.log_file)
        ensure_dir(path.parent)
        return path
    
    def get_checkpoint_path(self) -> Path:
        """获取检查点文件路径
        
        Returns:
            检查点文件路径
        """
        return Path(self.upload.checkpoint_file)
    
    def validate(self, config_path: Optional[str] = None) -> bool:
        """验证配置有效性

        Args:
            config_path: 配置文件路径（用于错误提示）

        Returns:
            是否有效
        """
        from utils import print_error, print_warning, print_info

        logger.debug("验证配置有效性")

        # 验证服务器地址
        if not self.server.base_url:
            logger.error("服务器地址未配置 (server.base_url)")
            print_error("服务器地址未配置")
            if config_path:
                print_info(f"  配置文件路径: {config_path}")
            print_info("  请检查配置文件中的 server.base_url 设置:")
            print("  server:")
            print('    base_url: "https://share.ustcer.top"')
            return False
        
        # 确保 URL 格式正确
        if not self.server.base_url.startswith(("http://", "https://")):
            logger.warning(f"服务器地址缺少协议，添加 https://: {self.server.base_url}")
            self.server.base_url = "https://" + self.server.base_url
        
        # 移除末尾的斜杠
        self.server.base_url = self.server.base_url.rstrip("/")
        
        # 验证超时时间
        if self.server.timeout < 1:
            logger.error("超时时间必须大于 0")
            return False
        
        # 验证重试次数
        if self.server.retry_count < 0:
            logger.error("重试次数不能为负数")
            return False
        
        # 验证日志级别
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.output.log_level.upper() not in valid_levels:
            logger.error(f"无效的日志级别: {self.output.log_level}")
            return False
        
        logger.debug("配置验证通过")
        return True
    
    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"Config(\n"
            f"  server={self.server},\n"
            f"  upload={self.upload},\n"
            f"  output={self.output},\n"
            f"  cache={self.cache},\n"
            f"  paths={self.paths}\n"
            f")"
        )


def find_config_file(explicit_path: Optional[str] = None) -> Optional[str]:
    """查找配置文件

    按以下顺序查找：
    1. 明确指定的路径
    2. 当前目录的 config.yaml
    3. 用户目录的 ~/.shareustc/config.yaml

    Args:
        explicit_path: 明确指定的配置文件路径

    Returns:
        找到的配置文件路径（绝对路径），如果没有则返回 None
    """
    # 1. 明确指定的路径
    if explicit_path:
        path = expand_path(explicit_path)
        abs_path = path.resolve() if not path.is_absolute() else path
        if path.exists():
            logger.debug(f"使用指定的配置文件: {abs_path}")
            return str(abs_path)
        else:
            logger.warning(f"指定的配置文件不存在: {abs_path}")
            return None

    # 2. 当前目录的 config.yaml
    current_dir_config = Path("config.yaml")
    if current_dir_config.exists():
        abs_path = current_dir_config.resolve()
        logger.debug(f"使用当前目录的配置文件: {abs_path}")
        return str(abs_path)

    # 3. 用户目录的 ~/.shareustc/config.yaml
    user_config = expand_path("~/.shareustc/config.yaml")
    if user_config.exists():
        abs_user_config = user_config.resolve() if not user_config.is_absolute() else user_config
        logger.debug(f"使用用户目录的配置文件: {abs_user_config}")
        return str(abs_user_config)

    logger.debug("未找到任何配置文件")
    return None


def get_default_config_path() -> Optional[str]:
    """获取默认配置文件路径
    
    Returns:
        默认配置文件路径，如果没有则返回 None
    """
    # 当前目录
    current_dir_config = Path("config.yaml")
    if current_dir_config.exists():
        return str(current_dir_config.absolute())
    
    # 用户目录
    user_config = expand_path("~/.shareustc/config.yaml")
    if user_config.exists():
        return str(user_config)
    
    return None


def load_config(config_path: Optional[str] = None) -> Config:
    """加载配置
    
    加载优先级（从高到低）：
    1. 明确指定的配置文件
    2. 当前目录的 config.yaml
    3. 用户目录的 ~/.shareustc/config.yaml
    4. 环境变量
    5. 默认配置（需要用户创建配置文件）
    
    Args:
        config_path: 明确指定的配置文件路径
        
    Returns:
        Config 实例
        
    Raises:
        FileNotFoundError: 未找到配置文件
        ValueError: 配置验证失败
    """
    logger.debug(f"开始加载配置，指定路径: {config_path}")
    
    # 1. 查找配置文件
    found_config_path = find_config_file(config_path)
    
    # 2. 从配置文件加载
    if found_config_path:
        config = Config.from_file(found_config_path)
        logger.info(f"已加载配置文件: {found_config_path}")
    else:
        # 没有找到配置文件
        if config_path:
            # 用户明确指定了配置文件但不存在
            raise FileNotFoundError(
                f"指定的配置文件不存在: {config_path}\n"
                f"请使用 --template 生成示例配置文件"
            )
        else:
            # 尝试查找默认配置文件但未找到
            raise FileNotFoundError(
                f"未找到配置文件。请在以下位置之一创建 config.yaml:\n"
                f"  1. 当前目录: {Path.cwd() / 'config.yaml'}\n"
                f"  2. 用户目录: {expand_path('~/.shareustc/config.yaml')}\n\n"
                f"使用以下命令生成示例配置文件:\n"
                f"  shareustc-upload --template\n"
                f"然后复制并重命名:\n"
                f"  cp config.example.yaml config.yaml\n"
                f"编辑 config.yaml 设置服务器地址"
            )
    
    # 3. 从环境变量加载（覆盖配置文件）
    env_config = Config.from_env()
    config = _merge_config(config, env_config)
    
    # 4. 验证配置
    if not config.validate(found_config_path):
        raise ValueError("配置验证失败")
    
    logger.debug(f"配置加载完成: {config}")
    return config


def _merge_config(base: Config, override: Config) -> Config:
    """合并两个配置，override 优先级更高

    只有当 override 中的值非空（非 None、非空字符串）时才会覆盖 base 中的值。

    Args:
        base: 基础配置
        override: 覆盖配置

    Returns:
        合并后的配置
    """
    base_dict = base.to_dict()
    override_dict = override.to_dict()

    def merge_dict(d1: Dict, d2: Dict) -> Dict:
        result = d1.copy()
        for key, value in d2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                result[key] = merge_dict(result[key], value)
            elif value not in (None, ""):  # 只覆盖非 None 且非空字符串的值
                result[key] = value
            # 如果 value 是 None 或空字符串，保留 result 中的原值
        return result

    merged = merge_dict(base_dict, override_dict)
    return Config.from_dict(merged)
