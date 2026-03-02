#!/usr/bin/env python3
"""大文件上传测试脚本

测试大文件上传功能，包括：
1. 流式上传是否正常
2. 进度条是否显示
3. 超时设置是否正确

使用方法:
    cd upload_tools
    python tests/test_large_upload.py --config config.yaml --size 50

参数:
    --config: 配置文件路径
    --size:   测试文件大小（MB）
    --cleanup: 测试完成后删除测试文件
"""

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import load_config, PathConfig, resolve_path
from auth import AuthManager
from uploader import BatchUploader
from csv_parser import UploadTask
from utils import format_file_size, print_info, print_success, print_error


def create_test_file(size_mb: int) -> Path:
    """创建指定大小的测试文件
    
    使用随机数据填充，模拟真实文件内容。
    
    Args:
        size_mb: 文件大小（MB）
        
    Returns:
        测试文件路径
    """
    # 创建临时文件
    fd, filepath = tempfile.mkstemp(suffix=".bin", prefix="test_upload_")
    os.close(fd)
    
    filepath = Path(filepath)
    chunk_size = 1024 * 1024  # 1MB
    total_bytes = size_mb * chunk_size
    
    print_info(f"创建测试文件: {filepath}")
    print_info(f"文件大小: {format_file_size(total_bytes)}")
    
    # 写入随机数据
    import random
    with open(filepath, 'wb') as f:
        written = 0
        while written < total_bytes:
            # 每次写入 1MB
            to_write = min(chunk_size, total_bytes - written)
            data = os.urandom(to_write)
            f.write(data)
            written += to_write
            
            # 显示进度
            if written % (10 * chunk_size) == 0:
                progress = (written / total_bytes) * 100
                print(f"  写入进度: {progress:.1f}%", end='\r')
    
    print()  # 换行
    print_success(f"测试文件创建完成: {format_file_size(filepath.stat().st_size)}")
    
    return filepath


def test_upload(filepath: Path, config_path: str):
    """测试上传功能
    
    Args:
        filepath: 测试文件路径
        config_path: 配置文件路径
    """
    print_info("加载配置...")
    config = load_config(config_path)
    
    # 创建 AuthManager
    print_info("初始化认证...")
    path_config = PathConfig.from_config(config.get("paths", {}))
    cookie_file = resolve_path(path_config.cookie_file)
    
    auth = AuthManager(
        base_url=config["server"]["base_url"],
        cookie_file=cookie_file,
    )
    
    # 检查登录状态
    if not auth.check_login():
        print_error("未登录，请先运行: python -m src.cli --login")
        sys.exit(1)
    
    print_success("已登录")
    
    # 创建上传器
    uploader = BatchUploader(
        base_url=config["server"]["base_url"],
        session=auth.session,
        timeout=600,  # 10分钟超时
    )
    
    # 创建上传任务
    task = UploadTask(
        file_path=filepath,
        title=f"测试大文件上传_{filepath.stat().st_size // (1024*1024)}MB",
        course_name="测试课程",
        resource_type="课件",
        category="测试",
        tags=["test", "large_file"],
        description=f"大文件上传测试，文件大小: {format_file_size(filepath.stat().st_size)}",
        row_number=1,
    )
    
    print_info("开始上传测试...")
    print(f"  文件: {filepath.name}")
    print(f"  大小: {format_file_size(filepath.stat().st_size)}")
    print()
    
    start_time = time.time()
    result = uploader.upload_single(task)
    duration = time.time() - start_time
    
    print()
    if result.success:
        print_success(f"✓ 上传成功！")
        print(f"  资源ID: {result.resource_id}")
        print(f"  耗时: {duration:.2f}秒")
        
        # 计算上传速度
        speed = filepath.stat().st_size / duration / (1024 * 1024)  # MB/s
        print(f"  平均速度: {speed:.2f} MB/s")
        
        return True
    else:
        print_error(f"✗ 上传失败")
        print(f"  错误: {result.error}")
        return False


def main():
    parser = argparse.ArgumentParser(description="大文件上传测试")
    parser.add_argument("--config", "-c", default="config.yaml",
                        help="配置文件路径 (默认: config.yaml)")
    parser.add_argument("--size", "-s", type=int, default=50,
                        help="测试文件大小（MB）(默认: 50)")
    parser.add_argument("--cleanup", action="store_true",
                        help="测试完成后删除测试文件")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("大文件上传测试")
    print("=" * 60)
    print()
    
    # 创建测试文件
    test_file = create_test_file(args.size)
    
    try:
        # 执行测试
        success = test_upload(test_file, args.config)
        
        if success:
            print()
            print("=" * 60)
            print_success("测试通过！大文件上传功能正常")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print_error("测试失败！请检查错误信息")
            print("=" * 60)
            sys.exit(1)
            
    finally:
        # 清理测试文件
        if args.cleanup and test_file.exists():
            print()
            print_info(f"删除测试文件: {test_file}")
            test_file.unlink()


if __name__ == "__main__":
    main()
