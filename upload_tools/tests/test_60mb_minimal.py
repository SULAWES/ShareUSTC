#!/usr/bin/env python3
"""60MB大文件上传测试 - 最小化版，禁用进度条"""

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
from utils import format_file_size, print_info, print_success, print_error
import json

def create_test_file(size_mb: int = 60) -> Path:
    fd, filepath = tempfile.mkstemp(suffix=".zip", prefix="test_60mb_")
    os.close(fd)
    filepath = Path(filepath)
    chunk_size = 1024 * 1024
    with open(filepath, 'wb') as f:
        for i in range(size_mb):
            f.write(os.urandom(chunk_size))
    return filepath

def main():
    print("=" * 60)
    print("60MB大文件上传测试（最小化版）")
    print("=" * 60)
    
    config = load_config('config.yaml')
    cookie_file = resolve_path(config.paths.cookie_file)
    
    auth = AuthManager(
        base_url=config.server.base_url,
        cookie_file=cookie_file,
    )
    
    if not auth.is_authenticated():
        print_error("未登录")
        sys.exit(1)
    
    print_success("已登录")
    
    # 创建60MB测试文件
    test_file = create_test_file(60)
    print(f"测试文件: {test_file} ({format_file_size(test_file.stat().st_size)})")
    
    url = f"{config.server.base_url}/api/resources"
    file_size = test_file.stat().st_size
    
    # 准备元数据
    metadata = {
        "title": "测试大文件上传_60MB",
        "courseName": "测试课程",
        "resourceType": "zip",
        "category": "other",
        "tags": ["test"],
        "description": "60MB大文件上传测试",
        "teacherSns": [],
        "courseSns": [],
    }
    
    print(f"\n开始上传到 {url}")
    print("禁用进度条，仅显示关键信息...")
    
    file_handle = open(test_file, 'rb')
    
    encoder = MultipartEncoder({
        'metadata': json.dumps(metadata, ensure_ascii=False),
        'file': (test_file.name, file_handle, 'application/zip'),
    })
    
    # 简化的进度回调 - 每10%打印一次
    last_percent = -1
    def callback(monitor):
        nonlocal last_percent
        percent = int((monitor.bytes_read / monitor.len) * 100)
        if percent >= last_percent + 10:
            print(f"  上传进度: {percent}% ({format_file_size(monitor.bytes_read)})")
            last_percent = percent
    
    monitor = MultipartEncoderMonitor(encoder, callback)
    
    headers = {'Content-Type': monitor.content_type}
    
    # 计算超时：60MB / 0.3MB/s = 200s，留3倍余量 = 600s = 10分钟
    timeout = (30, 600)
    
    print(f"超时设置: {timeout}")
    
    start_time = time.time()
    try:
        response = auth.session.post(
            url,
            data=monitor,
            headers=headers,
            timeout=timeout,
        )
        duration = time.time() - start_time
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}")
        
        if response.status_code == 201:
            data = response.json()
            print_success(f"✓ 上传成功！资源ID: {data.get('id')}")
            print(f"  耗时: {duration:.2f}秒")
            speed_mbps = file_size / duration / (1024 * 1024)
            print(f"  平均速度: {speed_mbps:.2f} MB/s")
        else:
            print_error(f"✗ 上传失败: HTTP {response.status_code}")
            
    except requests.exceptions.Timeout as e:
        print_error(f"✗ 请求超时: {e}")
    except requests.exceptions.ConnectionError as e:
        print_error(f"✗ 连接错误: {e}")
    except Exception as e:
        print_error(f"✗ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        file_handle.close()
        if test_file.exists():
            test_file.unlink()
            print("\n已清理测试文件")

if __name__ == "__main__":
    main()
