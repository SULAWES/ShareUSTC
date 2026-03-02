"""命令行界面

ShareUSTC 批量上传工具的命令行入口。
"""

import os
import sys
import logging
from pathlib import Path

import click
from tqdm import tqdm

from utils import (
    setup_logging, print_banner, print_success, 
    print_error, print_warning, print_info
)
from config import load_config, Config, get_default_config_path
from auth import AuthManager, interactive_login
from csv_parser import CSVParser
from matcher import EntityMatcher, match_task_entities
from uploader import BatchUploader, Checkpoint, resume_upload
from reporter import generate_reports


# 版本信息
VERSION = "0.1.0"


def generate_config_example(output_path: str = "config.example.yaml"):
    """生成配置文件示例
    
    Args:
        output_path: 输出文件路径
    """
    content = """# ShareUSTC 批量上传工具 - 配置文件
# 复制此文件为 config.yaml 并根据需要修改

# 服务器配置
server:
  # 平台服务器地址（必填）
  base_url: "https://share.ustcer.top"
  
  # HTTP 请求超时时间（秒）
  timeout: 300
  
  # 失败重试次数
  retry_count: 3
  
  # 重试间隔（秒）
  retry_delay: 2

# 上传配置
upload:
  # 最大文件大小（字节），默认 100MB
  max_file_size: 104857600
  
  # 上传缓冲区大小（字节）
  chunk_size: 8192

# 输出配置
output:
  # 报告格式：csv / html / both
  report_format: "csv"
  
  # 是否显示详细输出
  verbose: true
  
  # 日志级别：DEBUG / INFO / WARNING / ERROR
  log_level: "INFO"

# 缓存配置
cache:
  # 课程/教师列表缓存时间（秒）
  entity_cache_ttl: 3600

# 路径配置（可选，使用默认值时可删除）
# 默认使用当前目录下的 .shareustc/ 文件夹
paths:
  # Cookie 文件保存路径
  cookie_file: ".shareustc/cookies.json"
  
  # 日志文件路径
  log_file: ".shareustc/upload.log"
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


def generate_csv_example(output_path: str = "my_upload.example.csv"):
    """生成 CSV 文件示例
    
    Args:
        output_path: 输出文件路径
    """
    content = """title,course_name,related_courses,related_teachers,category,tags,description,file_path
2025年线性代数期中试卷,线性代数,线性代数I;线性代数II,张三;李四,past_paper,期中;2025;试卷,2025年春季学期期中考试试卷（含答案）,/path/to/exam1.pdf
微积分复习笔记,微积分,微积分上;微积分下,王五,note,复习;笔记;总结,第一章到第五章重点整理,/path/to/notes.md
计算机组成原理讲义,计算机组成原理,计算机组成原理,赵六,lecture,讲义;PPT,2025年春季课程讲义,/path/to/lecture.pptx
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


@click.command()
@click.option("--csv", "csv_path", type=click.Path(exists=True), help="CSV 文件路径（包含要上传的资源列表）")
@click.option("--config", "config_path", type=click.Path(), help="配置文件路径（默认使用当前目录或用户目录的 config.yaml）")
@click.option("--login", is_flag=True, help="仅执行登录操作（测试认证）")
@click.option("--logout", is_flag=True, help="登出并清除登录状态")
@click.option("--template", is_flag=True, help="在当前目录生成示例配置文件和 CSV 模板")
@click.option("--resume", is_flag=True, help="从上次中断处继续上传")
@click.option("--dry-run", is_flag=True, help="模拟运行，验证 CSV 格式和文件路径，不上传实际文件")
@click.option("--output", "output_path", type=click.Path(), help="报告输出目录（默认当前目录）")
@click.option("--format", "report_format", type=click.Choice(["csv", "html", "both"]), 
              default="csv", help="报告格式")
@click.option("--verbose", is_flag=True, help="显示详细日志（DEBUG 级别）")
@click.option("--non-interactive", is_flag=True, help="非交互式模式（模糊匹配时自动跳过，不提示选择）")
@click.version_option(version=VERSION, prog_name="shareustc-upload")
def main(csv_path, config_path, login, logout, template, resume, dry_run, output_path, 
         report_format, verbose, non_interactive):
    """ShareUSTC 批量上传工具
    
    使用 CSV 文件批量上传学习资料到 ShareUSTC 平台。
    
    准备工作:
    
        \b
        # 1. 生成示例配置文件和 CSV 模板
        shareustc-upload --template
        
        # 2. 复制并修改配置文件
        cp config.example.yaml config.yaml
        # 编辑 config.yaml，设置服务器地址等
        
        # 3. 填写 CSV 文件
        # 编辑 my_upload.example.csv 或创建新的 CSV 文件
    
    基本使用:
    
        \b
        # 测试登录
        shareustc-upload --login
        
        # 上传资源（使用当前目录的 config.yaml）
        shareustc-upload --csv my_upload.csv
        
        # 使用指定配置文件
        shareustc-upload --csv my_upload.csv --config /path/to/config.yaml
        
        # 断点续传
        shareustc-upload --csv my_upload.csv --resume
    
    配置文件说明:
    
        工具会按以下顺序查找配置文件：
        1. --config 参数指定的文件
        2. 当前目录的 config.yaml
        3. 用户目录的 ~/.shareustc/config.yaml
        
        配置文件中必须设置 server.base_url（服务器地址）
    """
    # 打印横幅
    print_banner()
    
    # 处理模板生成
    if template:
        config_example = generate_config_example()
        csv_example = generate_csv_example()
        print_success(f"已生成示例文件:")
        print(f"  - 配置文件示例: {config_example}")
        print(f"  - CSV 示例: {csv_example}")
        print()
        print_info("使用步骤:")
        print("  1. 复制 config.example.yaml 为 config.yaml")
        print("  2. 编辑 config.yaml，设置服务器地址")
        print("  3. 参考 my_upload.example.csv 创建你的 CSV 文件")
        print("  4. 运行: shareustc-upload --csv your_file.csv")
        return
    
    # 处理仅登录
    if login:
        print_info("登录模式 - 仅测试认证")
        
        try:
            config = load_config(config_path)
        except FileNotFoundError as e:
            print_error(str(e))
            sys.exit(1)
        except Exception as e:
            print_error(f"加载配置失败: {e}")
            print_info("提示: 使用 --template 生成示例配置文件")
            sys.exit(1)
        
        # 设置日志
        logger = setup_logging(
            log_level="DEBUG" if verbose else "INFO",
            log_file=str(config.get_log_path()) if config.get_log_path() else None
        )
        
        logger.info(f"服务器: {config.server.base_url}")

        # 初始化认证管理器
        auth = AuthManager(
            base_url=config.server.base_url,
            cookie_file=str(config.get_cookie_path()),
        )

        # 检查是否已登录
        if auth.is_authenticated():
            user = auth.get_user()
            print_info(f"当前已登录: {user.username} (ID: {user.id})")
            if not click.confirm("是否重新登录?"):
                print_info("保持当前登录状态")
                return
        
        # 执行登录
        if interactive_login(auth):
            user = auth.get_user()
            print_success(f"登录成功: {user.username}")
        else:
            print_error("登录失败")
            sys.exit(1)
        return
    
    # 处理登出
    if logout:
        try:
            config = load_config(config_path)
        except:
            config = Config()
        
        auth = AuthManager(
            base_url=config.server.base_url,
            cookie_file=str(config.get_cookie_path()),
        )
        
        auth.logout()
        print_success("已登出并清除登录状态")
        return
    
    # 检查必需参数（CSV 文件）
    if not csv_path:
        print_error("请指定 CSV 文件路径: --csv <path>")
        print_info("使用 --template 生成示例配置文件和 CSV 模板")
        print_info("使用 --login 测试登录")
        print_info("使用 --help 查看更多选项")
        sys.exit(1)
    
    # 加载配置
    try:
        config = load_config(config_path)
        # 命令行参数覆盖配置
        if verbose:
            config.output.verbose = True
            config.output.log_level = "DEBUG"
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)
    except Exception as e:
        print_error(f"加载配置失败: {e}")
        print_info("提示: 使用 --template 生成示例配置文件")
        sys.exit(1)
    
    # 设置日志
    logger = setup_logging(
        log_level=config.output.log_level,
        log_file=str(config.get_log_path()) if config.get_log_path() else None
    )
    
    logger.info(f"ShareUSTC 批量上传工具 v{VERSION}")
    logger.info(f"CSV 文件: {csv_path}")
    logger.info(f"服务器: {config.server.base_url}")
    logger.info(f"配置文件: {config_path or get_default_config_path() or '默认配置'}")
    
    # 初始化认证管理器
    auth = AuthManager(
        base_url=config.server.base_url,
        cookie_file=str(config.get_cookie_path()),
    )

    # 检查登录状态
    if not auth.is_authenticated():
        print_info("需要登录才能继续")
        if not interactive_login(auth):
            print_error("登录失败")
            sys.exit(1)

    # 确认登录状态
    if not auth.is_authenticated():
        print_error("登录状态无效")
        sys.exit(1)
    
    user = auth.get_user()
    print_success(f"已登录: {user.username}")
    logger.info(f"当前用户: {user.username} (ID: {user.id})")
    
    # 解析 CSV
    try:
        parser = CSVParser(max_file_size=config.upload.max_file_size)
        tasks = parser.parse(csv_path)
    except FileNotFoundError as e:
        print_error(f"CSV 文件不存在: {e}")
        sys.exit(1)
    except Exception as e:
        print_error(f"解析 CSV 失败: {e}")
        logger.exception("CSV 解析错误")
        sys.exit(1)
    
    if not tasks:
        print_warning("CSV 中没有有效的上传任务")
        sys.exit(0)
    
    print_success(f"成功解析 {len(tasks)} 个上传任务")
    
    # 验证任务
    validation = parser.validate_tasks(tasks)
    if validation["invalid"] > 0:
        print_warning(f"有 {validation['invalid']} 个任务验证失败")
        for error in validation["errors"]:
            print_error(f"  第 {error['row']} 行: {error['error']}")
        if validation["valid"] == 0:
            print_error("没有有效的任务可以上传")
            sys.exit(1)
    
    # 加载课程和教师列表
    print_info("正在加载课程和教师列表...")
    matcher = EntityMatcher(
        base_url=config.server.base_url,
        session=auth.get_session(),
        cache_ttl=config.cache.entity_cache_ttl,
    )
    matcher.load_entities()
    
    # 匹配实体
    print_info("正在匹配课程和教师信息...")
    tasks_to_upload = []
    for task in tasks:
        warnings, errors, should_upload = match_task_entities(
            task, matcher,
            interactive=(not non_interactive and not dry_run)
        )
        if warnings:
            for warning in warnings:
                print_warning(f"[{task.title}] {warning}")
        if should_upload:
            tasks_to_upload.append(task)
        else:
            print_info(f"跳过上传: {task.title}")

    # 更新任务列表
    original_count = len(tasks)
    tasks = tasks_to_upload
    skipped_count = original_count - len(tasks)
    if skipped_count > 0:
        print_info(f"共跳过 {skipped_count} 个资源")
    
    # 模拟运行模式
    if dry_run:
        print_info("模拟运行模式，不上传实际文件")
        print("\n将要上传的文件:")
        for i, task in enumerate(tasks, 1):
            print(f"  {i}. {task.title}")
            print(f"     文件: {task.file_path}")
            print(f"     分类: {task.category}")
            if task.matched_course_sns:
                print(f"     关联课程 SN: {task.matched_course_sns}")
            if task.matched_teacher_sns:
                print(f"     关联教师 SN: {task.matched_teacher_sns}")
        return
    
    # 处理断点续传
    checkpoint = Checkpoint(config.get_checkpoint_path())
    if resume:
        if checkpoint.load():
            print_info(f"从检查点恢复，已跳过 {len(checkpoint.completed_indices)} 个完成的任务")
            remaining_tasks = checkpoint.get_remaining_tasks(tasks)
            if not remaining_tasks:
                print_success("所有任务已完成！")
                return
            tasks = remaining_tasks
        else:
            print_warning("没有找到检查点，将从头开始上传")
    
    # 确认上传
    if not click.confirm(f"\n准备上传 {len(tasks)} 个文件，是否继续?"):
        print_info("已取消上传")
        return
    
    # 执行上传
    print()
    uploader = BatchUploader(
        base_url=config.server.base_url,
        session=auth.get_session(),
        timeout=config.server.timeout,
        retry_count=config.server.retry_count,
        retry_delay=config.server.retry_delay,
    )
    
    # 使用 tqdm 显示进度
    progress_bar = tqdm(total=len(tasks), desc="上传进度", unit="个")
    
    def progress_callback(current, total, task):
        progress_bar.set_postfix_str(f"当前: {task.title[:20]}...")
        progress_bar.update(1)
    
    try:
        if resume:
            results = resume_upload(checkpoint, tasks, uploader)
        else:
            results = uploader.upload(tasks, progress_callback)
        
        # 清除检查点（如果全部成功）
        if all(r.success for r in results):
            checkpoint.clear()
        else:
            # 保存失败的任务到检查点
            if csv_path:
                checkpoint.csv_path = csv_path
                for i, result in enumerate(results):
                    if not result.success:
                        checkpoint.mark_failed(i, result.task, result.error or "未知错误")
                checkpoint.save(csv_path)
    
    except KeyboardInterrupt:
        print_warning("\n用户中断上传")
        # 保存检查点
        if csv_path:
            checkpoint.csv_path = csv_path
            checkpoint.save(csv_path)
            print_info(f"已保存检查点，使用 --resume 继续上传")
        sys.exit(1)
    
    finally:
        progress_bar.close()
    
    # 生成报告
    print()
    output_dir = output_path if output_path else "."
    report_files = generate_reports(results, report_format, output_dir)
    
    for filepath in report_files:
        print_success(f"报告已保存: {filepath}")
    
    # 根据结果返回退出码
    success_count = sum(1 for r in results if r.success)
    if success_count == 0:
        sys.exit(2)  # 全部失败
    elif success_count < len(results):
        sys.exit(3)  # 部分失败
    else:
        print_success("全部上传成功！")
        sys.exit(0)


if __name__ == "__main__":
    main()
