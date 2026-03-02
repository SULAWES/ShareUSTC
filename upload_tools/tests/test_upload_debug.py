#!/usr/bin/env python3
"""上传测试 - 调试版"""

import sys
import os
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from config import load_config, resolve_path
from auth import AuthManager
from utils import format_file_size

def create_small_test_file(size_mb: int = 1) -> Path:
    """创建小测试文件（使用 .zip 扩展名）"""
    fd, filepath = tempfile.mkstemp(suffix=".zip", prefix="test_")
    os.close(fd)
    filepath = Path(filepath)
    with open(filepath, 'wb') as f:
        f.write(os.urandom(size_mb * 1024 * 1024))
    return filepath

def test_multipart_encoder():
    """测试 MultipartEncoder 是否正常工作"""
    print("=" * 60)
    print("测试 MultipartEncoder 流式上传")
    print("=" * 60)
    
    # 加载配置
    config = load_config('config.yaml')
    cookie_file = resolve_path(config.paths.cookie_file)
    
    # 创建 AuthManager
    auth = AuthManager(
        base_url=config.server.base_url,
        cookie_file=cookie_file,
    )
    
    if not auth.is_authenticated():
        print("未登录，请先运行: python -m src.cli --login")
        sys.exit(1)
    
    print(f"服务器: {config.server.base_url}")
    print(f"已认证: {auth.is_authenticated()}")
    
    # 创建10MB测试文件（超过大文件阈值）
    print("\n创建 10MB 测试文件...")
    test_file = create_small_test_file(10)
    
    try:
        url = f"{config.server.base_url}/api/resources"
        file_size = test_file.stat().st_size
        
        print(f"文件大小: {format_file_size(file_size)}")
        print(f"上传 URL: {url}")
        
        # 准备元数据
        import json
        # 注意：resourceType 必须是服务器支持的枚举值
        metadata = {
            "title": "测试流式上传_10MB",
            "courseName": "测试课程",
            "resourceType": "zip",  # 必须是: pdf, doc, docx, ppt, pptx, txt, web_markdown, jpeg, jpg, png, zip, other
            "category": "other",
            "tags": ["test"],
            "description": "测试 MultipartEncoder 流式上传",
            "teacherSns": [],
            "courseSns": [],
        }
        
        # 打开文件
        file_handle = open(test_file, 'rb')
        
        # 创建 MultipartEncoder
        encoder = MultipartEncoder({
            'metadata': json.dumps(metadata, ensure_ascii=False),
            'file': (test_file.name, file_handle, 'application/octet-stream'),
        })
        
        print(f"Content-Type: {encoder.content_type}")
        print(f"Content-Length: {format_file_size(encoder.len)}")
        
        # 设置请求头
        headers = {
            'Content-Type': encoder.content_type,
        }
        
        # 添加 Cookie
        session_cookies = auth.session.cookies.get_dict()
        print(f"\n发送请求...")
        print(f"Cookie: {session_cookies}")
        
        # 发送请求
        timeout = (30, 300)  # (连接超时30s, 读取超时300s)
        
        try:
            response = auth.session.post(
                url,
                data=encoder,
                headers=headers,
                timeout=timeout,
            )
            
            print(f"\n响应状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            
            if response.status_code == 201:
                print("\n✓ 上传成功！")
                data = response.json()
                print(f"  资源ID: {data.get('id')}")
            else:
                print(f"\n✗ 上传失败: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout as e:
            print(f"\n✗ 请求超时: {e}")
        except requests.exceptions.ConnectionError as e:
            print(f"\n✗ 连接错误: {e}")
        except Exception as e:
            print(f"\n✗ 错误: {type(e).__name__}: {e}")
        finally:
            file_handle.close()
        
    finally:
        if test_file.exists():
            test_file.unlink()
            print("\n已清理测试文件")

if __name__ == "__main__":
    test_multipart_encoder()
