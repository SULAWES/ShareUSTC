#!/usr/bin/env python3
"""60MB大文件上传测试 - 简化版"""

import sys
import os
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import load_config, resolve_path
from auth import AuthManager
from uploader import BatchUploader
from csv_parser import UploadTask
from utils import format_file_size, print_info, print_success, print_error

def create_test_file(size_mb: int = 60) -> Path:
    # 使用 .zip 扩展名，因为服务器只支持特定文件类型
    fd, filepath = tempfile.mkstemp(suffix=".zip", prefix="test_60mb_")
    os.close(fd)
    filepath = Path(filepath)
    chunk_size = 1024 * 1024
    total_bytes = size_mb * chunk_size
    
    print(f"创建 {size_mb}MB 测试文件...")
    with open(filepath, 'wb') as f:
        for i in range(size_mb):
            f.write(os.urandom(chunk_size))
            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{size_mb}MB")
    
    print(f"✓ 测试文件: {filepath} ({format_file_size(filepath.stat().st_size)})")
    return filepath

def main():
    print("=" * 60)
    print("60MB大文件上传测试")
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
        print_error("未登录，请先运行: python -m src.cli --login")
        sys.exit(1)
    
    print_success("已登录")
    
    # 创建60MB测试文件
    test_file = create_test_file(60)
    
    try:
        # 创建上传器
        uploader = BatchUploader(
            base_url=config.server.base_url,
            session=auth.session,
            timeout=300,
        )
        
        # 创建上传任务 - infer_resource_type 会根据 .zip 扩展名自动推断类型
        task = UploadTask(
            file_path=test_file,
            title="测试大文件上传_60MB",
            course_name="测试课程",
            resource_type=None,  # 让 infer_resource_type 自动推断
            category="other",
            tags=["test", "large_file"],
            description="60MB大文件上传测试，验证流式上传功能",
            row_number=1,
        )
        
        print()
        print("开始上传...")
        print(f"文件大小: {format_file_size(test_file.stat().st_size)}")
        print(f"预估时间: ~60-120秒 (按1MB/s计算)")
        print("-" * 60)
        
        start_time = time.time()
        result = uploader.upload_single(task)
        duration = time.time() - start_time
        
        print()
        print("=" * 60)
        if result.success:
            print_success(f"✓ 上传成功！")
            print(f"  资源ID: {result.resource_id}")
            print(f"  耗时: {duration:.2f}秒")
            speed_mbps = test_file.stat().st_size / duration / (1024 * 1024)
            print(f"  平均速度: {speed_mbps:.2f} MB/s")
        else:
            print_error(f"✗ 上传失败: {result.error}")
        print("=" * 60)
        
    finally:
        if test_file.exists():
            test_file.unlink()
            print(f"\n已清理测试文件")

if __name__ == "__main__":
    main()
