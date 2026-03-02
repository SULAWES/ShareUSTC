#!/usr/bin/env python3
"""配置诊断脚本 - 帮助诊断配置文件问题"""

import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

import yaml
from config import find_config_file, Config, load_config
from utils import expand_path

def main():
    print("=" * 60)
    print("配置诊断工具")
    print("=" * 60)
    print()

    # 显示当前工作目录
    cwd = Path.cwd()
    print(f"当前工作目录: {cwd}")
    print()

    # 检查当前目录的 config.yaml
    current_config = cwd / "config.yaml"
    print(f"1. 检查当前目录配置文件: {current_config}")
    print(f"   文件存在: {current_config.exists()}")
    if current_config.exists():
        print(f"   文件大小: {current_config.stat().st_size} 字节")
        try:
            with open(current_config, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"   文件内容:")
            print("-" * 40)
            print(content)
            print("-" * 40)
            try:
                data = yaml.safe_load(content)
                print(f"   YAML 解析结果: {data}")
                if data and "server" in data:
                    print(f"   server 配置: {data['server']}")
                    if "base_url" in data["server"]:
                        print(f"   base_url: '{data['server']['base_url']}'")
                    else:
                        print("   ⚠️ 警告: server 中缺少 base_url")
                else:
                    print("   ⚠️ 警告: 配置中缺少 server 部分")
            except Exception as e:
                print(f"   ❌ YAML 解析错误: {e}")
        except Exception as e:
            print(f"   ❌ 读取文件错误: {e}")
    print()

    # 使用 find_config_file 查找配置
    print("2. 使用 find_config_file 查找配置:")
    found_path = find_config_file()
    if found_path:
        print(f"   找到配置文件: {found_path}")
    else:
        print("   未找到配置文件")
    print()

    # 尝试加载配置
    print("3. 尝试加载配置:")
    try:
        config = load_config()
        print(f"   配置加载成功!")
        print(f"   server.base_url: '{config.server.base_url}'")
        print(f"   server.timeout: {config.server.timeout}")
        print(f"   server.retry_count: {config.server.retry_count}")
    except FileNotFoundError as e:
        print(f"   ❌ 文件未找到: {e}")
    except ValueError as e:
        print(f"   ❌ 配置验证失败: {e}")
    except Exception as e:
        print(f"   ❌ 其他错误: {e}")
        import traceback
        traceback.print_exc()
    print()

    # 检查用户目录配置
    user_config = expand_path("~/.shareustc/config.yaml")
    print(f"4. 检查用户目录配置文件: {user_config}")
    print(f"   文件存在: {user_config.exists()}")
    if user_config.exists():
        abs_path = user_config.resolve() if not user_config.is_absolute() else user_config
        print(f"   绝对路径: {abs_path}")
    print()

    print("=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
