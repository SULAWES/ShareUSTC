"""认证模块

管理用户认证状态，包括登录、Token 刷新、Cookie 持久化等。
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

import requests

from utils import expand_path

logger = logging.getLogger("shareustc_upload")


@dataclass
class UserInfo:
    """用户信息"""
    id: str
    username: str
    email: Optional[str] = None
    role: str = "user"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserInfo":
        """从字典创建"""
        return cls(
            id=data.get("id", ""),
            username=data.get("username", ""),
            email=data.get("email"),
            role=data.get("role", "user"),
        )


class AuthManager:
    """认证管理器
    
    管理用户登录状态和 Cookie。
    """
    
    def __init__(self, base_url: str, cookie_file: str):
        """初始化认证管理器
        
        Args:
            base_url: API 基础 URL
            cookie_file: Cookie 文件路径
        """
        self.base_url = base_url.rstrip("/")
        self.cookie_file = expand_path(cookie_file)
        self.session = requests.Session()
        self.user: Optional[UserInfo] = None
        
        # 尝试加载已有 Cookie
        self._load_cookies()
        
        logger.debug(f"AuthManager 初始化完成，base_url: {base_url}")
    
    def _load_cookies(self) -> bool:
        """从文件加载 Cookie
        
        Returns:
            是否成功加载
        """
        if not self.cookie_file.exists():
            logger.debug(f"Cookie 文件不存在: {self.cookie_file}")
            return False
        
        try:
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            cookies = data.get("cookies", {})
            for name, value in cookies.items():
                self.session.cookies.set(name, value)
            
            self.user = UserInfo.from_dict(data.get("user", {}))
            
            logger.debug(f"已加载 Cookie: {list(cookies.keys())}")
            logger.info(f"已加载保存的登录状态，用户: {self.user.username if self.user else 'unknown'}")
            return True
            
        except Exception as e:
            logger.warning(f"加载 Cookie 失败: {e}")
            return False
    
    def _save_cookies(self) -> bool:
        """保存 Cookie 到文件
        
        Returns:
            是否成功保存
        """
        try:
            # 确保目录存在
            self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 收集 Cookie
            cookies = {}
            for cookie in self.session.cookies:
                cookies[cookie.name] = cookie.value
            
            # 保存数据
            data = {
                "cookies": cookies,
                "user": asdict(self.user) if self.user else {},
            }
            
            # 写入文件（只有当前用户可读写）
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            # 设置文件权限（仅当前用户可读写）
            os.chmod(self.cookie_file, 0o600)
            
            logger.debug(f"Cookie 已保存到: {self.cookie_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存 Cookie 失败: {e}")
            return False
    
    def login(self, username: str, password: str) -> bool:
        """用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            是否登录成功
        """
        logger.info(f"正在登录用户: {username}")
        
        url = f"{self.base_url}/api/auth/login"
        payload = {
            "username": username,
            "password": password
        }
        
        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=30
            )
            
            logger.debug(f"登录响应状态码: {response.status_code}")
            logger.debug(f"登录响应: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                self.user = UserInfo.from_dict(data)
                self._save_cookies()
                logger.info(f"登录成功！用户: {self.user.username} (ID: {self.user.id})")
                return True
            elif response.status_code == 400:
                error_msg = response.json().get("message", "用户名或密码错误")
                logger.error(f"登录失败: {error_msg}")
                return False
            else:
                logger.error(f"登录失败，服务器返回: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接服务器失败: {e}")
            return False
        except requests.exceptions.Timeout:
            logger.error("登录请求超时")
            return False
        except Exception as e:
            logger.error(f"登录时发生错误: {e}")
            return False
    
    def logout(self) -> bool:
        """用户登出
        
        Returns:
            是否登出成功
        """
        logger.info("正在登出...")
        
        try:
            url = f"{self.base_url}/api/auth/logout"
            self.session.post(url, timeout=10)
        except Exception as e:
            logger.debug(f"登出请求失败（可忽略）: {e}")
        finally:
            # 清除本地状态
            self.session.cookies.clear()
            self.user = None
            
            # 删除 Cookie 文件
            if self.cookie_file.exists():
                try:
                    self.cookie_file.unlink()
                    logger.debug(f"已删除 Cookie 文件: {self.cookie_file}")
                except Exception as e:
                    logger.warning(f"删除 Cookie 文件失败: {e}")
        
        logger.info("登出完成")
        return True
    
    def is_authenticated(self) -> bool:
        """检查是否已认证

        通过调用 /api/users/me 验证当前会话是否有效。

        Returns:
            是否已认证
        """
        if not self.user:
            logger.debug("用户未登录（无用户信息）")
            return False

        try:
            url = f"{self.base_url}/api/users/me"
            response = self.session.get(url, timeout=10)

            logger.debug(f"验证登录状态: {response.status_code}")

            if response.status_code == 200:
                # 更新用户信息
                data = response.json()
                self.user = UserInfo.from_dict(data)
                logger.debug(f"登录状态有效，用户: {self.user.username}")
                return True
            elif response.status_code == 401:
                logger.debug("登录状态已过期")
                return False
            else:
                logger.warning(f"验证登录状态时服务器返回: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.warning(f"验证登录状态时网络错误: {e}")
            return False
        except Exception as e:
            logger.error(f"验证登录状态时发生错误: {e}")
            return False
    
    def ensure_authenticated(self) -> bool:
        """确保已认证，如果未认证则提示登录
        
        Returns:
            是否已认证
        """
        if self.is_authenticated():
            return True
        
        logger.info("需要登录才能继续")
        return False
    
    def refresh_token(self) -> bool:
        """刷新 Token
        
        Returns:
            是否刷新成功
        """
        logger.debug("尝试刷新 Token...")
        
        try:
            url = f"{self.base_url}/api/auth/refresh"
            response = self.session.post(url, timeout=10)
            
            logger.debug(f"刷新 Token 响应: {response.status_code}")
            
            if response.status_code == 200:
                # 保存新的 Cookie
                self._save_cookies()
                logger.debug("Token 刷新成功")
                return True
            else:
                logger.warning(f"Token 刷新失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"刷新 Token 时发生错误: {e}")
            return False
    
    def get_session(self) -> requests.Session:
        """获取已配置好的 Session
        
        Returns:
            requests Session 对象
        """
        return self.session
    
    def get_user(self) -> Optional[UserInfo]:
        """获取当前用户信息
        
        Returns:
            用户信息，如果未登录则返回 None
        """
        return self.user
    
    def get_auth_headers(self) -> Dict[str, str]:
        """获取认证头
        
        注意：实际使用 Cookie 认证，此方法主要用于特殊情况。
        
        Returns:
            认证头字典
        """
        # 从 Cookie 中获取 token
        access_token = self.session.cookies.get("access_token")
        if access_token:
            return {"Authorization": f"Bearer {access_token}"}
        return {}


def interactive_login(auth_manager: AuthManager) -> bool:
    """交互式登录
    
    在命令行中提示用户输入用户名和密码。
    
    Args:
        auth_manager: 认证管理器实例
        
    Returns:
        是否登录成功
    """
    import getpass
    
    print("\n请登录 ShareUSTC 平台")
    print("-" * 40)
    
    username = input("用户名: ").strip()
    if not username:
        print("用户名不能为空")
        return False
    
    password = getpass.getpass("密码: ").strip()
    if not password:
        print("密码不能为空")
        return False
    
    return auth_manager.login(username, password)
