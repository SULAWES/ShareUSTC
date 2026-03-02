"""报告生成模块

生成上传结果报告，支持 CSV 和 HTML 格式。
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from html import escape

from uploader import UploadResult
from utils import format_file_size, get_timestamp, print_success, print_error, print_warning

logger = logging.getLogger("shareustc_upload")


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = "."):
        """初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"ReportGenerator 初始化，output_dir: {output_dir}")
    
    def generate_csv(self, results: List[UploadResult], filename: Optional[str] = None) -> str:
        """生成 CSV 报告
        
        Args:
            results: 上传结果列表
            filename: 文件名，默认自动生成
            
        Returns:
            生成的文件路径
        """
        if filename is None:
            filename = f"upload_report_{get_timestamp()}.csv"
        
        filepath = self.output_dir / filename
        logger.info(f"正在生成 CSV 报告: {filepath}")
        
        fieldnames = [
            "row_number",
            "title",
            "file_path",
            "status",
            "resource_id",
            "message",
            "error",
            "duration",
        ]
        
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                row = {
                    "row_number": result.task.row_number,
                    "title": result.task.title,
                    "file_path": str(result.task.file_path),
                    "status": "成功" if result.success else "失败",
                    "resource_id": result.resource_id or "",
                    "message": result.message,
                    "error": result.error or "",
                    "duration": f"{result.duration:.2f}s",
                }
                writer.writerow(row)
        
        logger.info(f"CSV 报告已生成: {filepath}")
        return str(filepath)
    
    def generate_html(self, results: List[UploadResult], filename: Optional[str] = None) -> str:
        """生成 HTML 报告
        
        Args:
            results: 上传结果列表
            filename: 文件名，默认自动生成
            
        Returns:
            生成的文件路径
        """
        if filename is None:
            filename = f"upload_report_{get_timestamp()}.html"
        
        filepath = self.output_dir / filename
        logger.info(f"正在生成 HTML 报告: {filepath}")
        
        # 统计数据
        total = len(results)
        success_count = sum(1 for r in results if r.success)
        failed_count = total - success_count
        total_duration = sum(r.duration for r in results)
        
        # 生成 HTML
        html_content = self._build_html(results, {
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "duration": total_duration,
        })
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"HTML 报告已生成: {filepath}")
        return str(filepath)
    
    def _build_html(self, results: List[UploadResult], stats: Dict[str, Any]) -> str:
        """构建 HTML 内容
        
        Args:
            results: 上传结果列表
            stats: 统计数据
            
        Returns:
            HTML 字符串
        """
        # 按成功/失败分组
        success_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShareUSTC 批量上传报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .stat-number {{
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{ color: #666; font-size: 14px; }}
        .stat-success {{ color: #52c41a; }}
        .stat-failed {{ color: #f5222d; }}
        .stat-total {{ color: #1890ff; }}
        .content {{ padding: 30px; }}
        .section {{ margin-bottom: 30px; }}
        .section-title {{
            font-size: 20px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e8e8e8;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e8e8e8;
        }}
        th {{
            background: #fafafa;
            font-weight: 600;
            color: #666;
        }}
        tr:hover {{ background: #f5f5f5; }}
        .status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }}
        .status-success {{
            background: #f6ffed;
            color: #52c41a;
            border: 1px solid #b7eb8f;
        }}
        .status-failed {{
            background: #fff1f0;
            color: #f5222d;
            border: 1px solid #ffa39e;
        }}
        .resource-id {{
            font-family: monospace;
            font-size: 12px;
            color: #1890ff;
            word-break: break-all;
        }}
        .error-message {{
            color: #f5222d;
            font-size: 13px;
            max-width: 300px;
            word-break: break-word;
        }}
        .file-path {{
            color: #666;
            font-size: 13px;
            max-width: 300px;
            word-break: break-all;
        }}
        .footer {{
            padding: 20px;
            text-align: center;
            color: #999;
            font-size: 12px;
            border-top: 1px solid #e8e8e8;
        }}
        .empty {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ShareUSTC 批量上传报告</h1>
            <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number stat-total">{stats["total"]}</div>
                <div class="stat-label">总计</div>
            </div>
            <div class="stat-card">
                <div class="stat-number stat-success">{stats["success"]}</div>
                <div class="stat-label">成功</div>
            </div>
            <div class="stat-card">
                <div class="stat-number stat-failed">{stats["failed"]}</div>
                <div class="stat-label">失败</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats["duration"]:.1f}s</div>
                <div class="stat-label">总耗时</div>
            </div>
        </div>
        
        <div class="content">
"""
        
        # 失败列表
        if failed_results:
            html += f"""
            <div class="section">
                <h2 class="section-title">❌ 失败列表 ({len(failed_results)})</h2>
                <table>
                    <thead>
                        <tr>
                            <th>行号</th>
                            <th>标题</th>
                            <th>文件路径</th>
                            <th>错误信息</th>
                        </tr>
                    </thead>
                    <tbody>
"""
            for result in failed_results:
                html += f"""
                        <tr>
                            <td>{result.task.row_number}</td>
                            <td>{escape(result.task.title)}</td>
                            <td class="file-path">{escape(str(result.task.file_path))}</td>
                            <td class="error-message">{escape(result.error or "未知错误")}</td>
                        </tr>
"""
            html += """
                    </tbody>
                </table>
            </div>
"""
        
        # 成功列表
        if success_results:
            html += f"""
            <div class="section">
                <h2 class="section-title">✅ 成功列表 ({len(success_results)})</h2>
                <table>
                    <thead>
                        <tr>
                            <th>行号</th>
                            <th>标题</th>
                            <th>资源ID</th>
                            <th>耗时</th>
                        </tr>
                    </thead>
                    <tbody>
"""
            for result in success_results:
                html += f"""
                        <tr>
                            <td>{result.task.row_number}</td>
                            <td>{escape(result.task.title)}</td>
                            <td class="resource-id">{result.resource_id or "-"}</td>
                            <td>{result.duration:.2f}s</td>
                        </tr>
"""
            html += """
                    </tbody>
                </table>
            </div>
"""
        
        html += """
        </div>
        
        <div class="footer">
            <p>由 ShareUSTC 批量上传工具生成</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def print_summary(self, results: List[UploadResult]):
        """打印汇总信息到控制台
        
        Args:
            results: 上传结果列表
        """
        total = len(results)
        success_count = sum(1 for r in results if r.success)
        failed_count = total - success_count
        total_duration = sum(r.duration for r in results)
        
        print("\n" + "=" * 50)
        print("上传结果汇总")
        print("=" * 50)
        print(f"总计: {total} 个文件")
        print_success(f"成功: {success_count} 个")
        if failed_count > 0:
            print_error(f"失败: {failed_count} 个")
        else:
            print(f"失败: {failed_count} 个")
        print(f"总耗时: {total_duration:.2f} 秒")
        
        if failed_count > 0:
            print("\n失败详情:")
            for result in results:
                if not result.success:
                    print_error(f"  - 第 {result.task.row_number} 行: {result.task.title}")
                    print(f"    错误: {result.error}")
        
        print("=" * 50)


def generate_reports(
    results: List[UploadResult],
    report_format: str = "csv",
    output_dir: str = ".",
) -> List[str]:
    """生成报告
    
    Args:
        results: 上传结果列表
        report_format: 报告格式 (csv/html/both)
        output_dir: 输出目录
        
    Returns:
        生成的文件路径列表
    """
    generator = ReportGenerator(output_dir)
    files = []
    
    if report_format in ("csv", "both"):
        csv_path = generator.generate_csv(results)
        files.append(csv_path)
    
    if report_format in ("html", "both"):
        html_path = generator.generate_html(results)
        files.append(html_path)
    
    # 打印汇总
    generator.print_summary(results)
    
    return files
