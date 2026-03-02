"""CSV 解析模块

解析用户提供的 CSV 文件，提取上传任务信息。
"""

import csv
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from utils import infer_resource_type, validate_category

logger = logging.getLogger("shareustc_upload")


@dataclass
class UploadTask:
    """上传任务
    
    表示 CSV 中的一行数据，对应一个待上传的资源。
    """
    # 基本信息
    title: str
    category: str
    file_path: Path
    
    # 可选信息
    course_name: Optional[str] = None
    related_courses: List[str] = None  # 原始课程名称列表
    related_teachers: List[str] = None  # 原始教师名称列表
    tags: List[str] = None
    description: Optional[str] = None
    
    # 元数据（从文件推断或用户指定）
    resource_type: Optional[str] = None
    mime_type: Optional[str] = None
    
    # 原始行号（用于错误定位）
    row_number: int = 0
    
    # 匹配结果（由 matcher 填充）
    matched_course_sns: List[int] = None
    matched_teacher_sns: List[int] = None
    
    def __post_init__(self):
        """初始化后的处理"""
        if self.related_courses is None:
            self.related_courses = []
        if self.related_teachers is None:
            self.related_teachers = []
        if self.tags is None:
            self.tags = []
        if self.matched_course_sns is None:
            self.matched_course_sns = []
        if self.matched_teacher_sns is None:
            self.matched_teacher_sns = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "course_name": self.course_name,
            "category": self.category,
            "file_path": str(self.file_path),
            "tags": self.tags,
            "description": self.description,
            "row_number": self.row_number,
        }


class CSVParserError(Exception):
    """CSV 解析错误"""
    pass


class ValidationError(Exception):
    """数据验证错误"""
    pass


class CSVParser:
    """CSV 解析器"""
    
    # CSV 必需字段
    REQUIRED_FIELDS = ["title", "category", "file_path"]
    
    # 支持的字段
    SUPPORTED_FIELDS = [
        "title", "course_name", "related_courses", "related_teachers",
        "category", "tags", "description", "file_path"
    ]
    
    def __init__(self, max_file_size: int = 104857600):
        """初始化 CSV 解析器
        
        Args:
            max_file_size: 最大文件大小（字节），默认 100MB
        """
        self.max_file_size = max_file_size
        logger.debug(f"CSVParser 初始化，max_file_size: {max_file_size}")
    
    def parse(self, csv_path: str) -> List[UploadTask]:
        """解析 CSV 文件
        
        Args:
            csv_path: CSV 文件路径
            
        Returns:
            上传任务列表
            
        Raises:
            CSVParserError: 解析错误
            FileNotFoundError: 文件不存在
        """
        csv_path = Path(csv_path)
        logger.info(f"正在解析 CSV 文件: {csv_path}")
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")
        
        if not csv_path.is_file():
            raise CSVParserError(f"路径不是文件: {csv_path}")
        
        tasks = []
        
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                # 检测 CSV 格式
                sample = f.read(8192)
                f.seek(0)
                
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample, delimiters=",;	")
                    logger.debug(f"检测到 CSV 分隔符: '{dialect.delimiter}'")
                except csv.Error:
                    dialect = csv.excel
                    logger.debug("使用默认 CSV 格式")
                
                reader = csv.DictReader(f, dialect=dialect)
                
                # 验证表头
                self._validate_headers(reader.fieldnames)
                
                # 解析每一行
                for row_number, row in enumerate(reader, start=2):  # 从 2 开始（第 1 行是表头）
                    try:
                        task = self._parse_row(row, row_number)
                        tasks.append(task)
                        logger.debug(f"第 {row_number} 行解析成功: {task.title}")
                    except ValidationError as e:
                        logger.warning(f"第 {row_number} 行验证失败: {e}")
                        raise ValidationError(f"第 {row_number} 行: {e}")
                    except Exception as e:
                        logger.error(f"第 {row_number} 行解析错误: {e}")
                        raise CSVParserError(f"第 {row_number} 行解析错误: {e}")
        
        except UnicodeDecodeError as e:
            raise CSVParserError(f"CSV 文件编码错误，请使用 UTF-8 编码: {e}")
        except Exception as e:
            if isinstance(e, (CSVParserError, ValidationError, FileNotFoundError)):
                raise
            raise CSVParserError(f"解析 CSV 文件时发生错误: {e}")
        
        logger.info(f"CSV 解析完成，共 {len(tasks)} 个任务")
        return tasks
    
    def _validate_headers(self, headers: Optional[List[str]]):
        """验证 CSV 表头
        
        Args:
            headers: 表头列表
            
        Raises:
            CSVParserError: 表头验证失败
        """
        if not headers:
            raise CSVParserError("CSV 文件没有表头")
        
        logger.debug(f"CSV 表头: {headers}")
        
        # 标准化表头（去除空白，转小写）
        normalized_headers = [h.strip().lower() if h else "" for h in headers]
        
        # 检查必需字段
        missing_fields = []
        for field in self.REQUIRED_FIELDS:
            if field not in normalized_headers:
                missing_fields.append(field)
        
        if missing_fields:
            raise CSVParserError(
                f"CSV 缺少必需字段: {', '.join(missing_fields)}\n"
                f"必需字段: {', '.join(self.REQUIRED_FIELDS)}\n"
                f"当前表头: {', '.join(headers)}"
            )
        
        # 检查不支持的字段（警告）
        unsupported = []
        for header in normalized_headers:
            if header and header not in self.SUPPORTED_FIELDS:
                unsupported.append(header)
        
        if unsupported:
            logger.warning(f"CSV 包含不支持的字段（将被忽略）: {', '.join(unsupported)}")
        
        logger.debug("表头验证通过")
    
    def _parse_row(self, row: Dict[str, str], row_number: int) -> UploadTask:
        """解析单行数据
        
        Args:
            row: 行数据字典
            row_number: 行号
            
        Returns:
            UploadTask 对象
            
        Raises:
            ValidationError: 验证失败
        """
        # 标准化键名（去除空白，转小写）
        normalized_row = {k.strip().lower() if k else "": v for k, v in row.items()}
        
        # 提取必需字段
        title = self._get_field(normalized_row, "title", required=True)
        category = self._get_field(normalized_row, "category", required=True)
        file_path_str = self._get_field(normalized_row, "file_path", required=True)
        
        # 验证和标准化分类
        try:
            category = validate_category(category)
        except ValueError as e:
            raise ValidationError(f"分类错误: {e}")
        
        # 处理文件路径
        file_path = Path(file_path_str).expanduser()
        
        # 检查文件是否存在
        if not file_path.exists():
            raise ValidationError(f"文件不存在: {file_path}")
        
        if not file_path.is_file():
            raise ValidationError(f"路径不是文件: {file_path}")
        
        # 检查文件大小
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            max_size_mb = self.max_file_size / 1024 / 1024
            file_size_mb = file_size / 1024 / 1024
            raise ValidationError(
                f"文件过大 ({file_size_mb:.2f}MB)，最大允许 {max_size_mb:.0f}MB: {file_path}"
            )
        
        if file_size == 0:
            raise ValidationError(f"文件为空: {file_path}")
        
        # 推断资源类型
        try:
            resource_type, mime_type = infer_resource_type(str(file_path))
        except ValueError as e:
            raise ValidationError(f"文件类型错误: {e}")
        
        # 提取可选字段
        course_name = self._get_field(normalized_row, "course_name")
        
        # 解析列表字段（分号分隔）
        related_courses = self._parse_list_field(normalized_row, "related_courses")
        related_teachers = self._parse_list_field(normalized_row, "related_teachers")
        tags = self._parse_list_field(normalized_row, "tags")
        
        description = self._get_field(normalized_row, "description")
        
        # 创建任务
        task = UploadTask(
            title=title,
            category=category,
            file_path=file_path,
            course_name=course_name,
            related_courses=related_courses,
            related_teachers=related_teachers,
            tags=tags,
            description=description,
            resource_type=resource_type,
            mime_type=mime_type,
            row_number=row_number,
        )
        
        return task
    
    def _get_field(self, row: Dict[str, str], field: str, required: bool = False) -> Optional[str]:
        """获取字段值
        
        Args:
            row: 行数据
            field: 字段名
            required: 是否必需
            
        Returns:
            字段值，如果为空且非必需则返回 None
            
        Raises:
            ValidationError: 必需字段为空
        """
        value = row.get(field, "").strip()
        
        if not value:
            if required:
                raise ValidationError(f"字段 '{field}' 不能为空")
            return None
        
        return value
    
    def _parse_list_field(self, row: Dict[str, str], field: str) -> List[str]:
        """解析列表字段（分号分隔）
        
        Args:
            row: 行数据
            field: 字段名
            
        Returns:
            字符串列表
        """
        value = row.get(field, "").strip()
        
        if not value:
            return []
        
        # 支持中英文分号和逗号分隔
        separators = [";", "；", ","]
        
        items = [value]
        for sep in separators:
            new_items = []
            for item in items:
                new_items.extend(item.split(sep))
            items = new_items
        
        # 清理空白
        items = [item.strip() for item in items if item.strip()]
        
        return items
    
    def validate_tasks(self, tasks: List[UploadTask]) -> Dict[str, Any]:
        """验证任务列表
        
        Args:
            tasks: 任务列表
            
        Returns:
            验证结果字典
        """
        logger.info("正在验证任务列表...")
        
        total = len(tasks)
        valid = 0
        invalid = 0
        errors = []
        
        for task in tasks:
            try:
                # 基本验证已在解析时完成，这里做额外检查
                if not task.file_path.exists():
                    raise ValidationError(f"文件不存在: {task.file_path}")
                
                valid += 1
                
            except ValidationError as e:
                invalid += 1
                errors.append({
                    "row": task.row_number,
                    "title": task.title,
                    "error": str(e)
                })
                logger.warning(f"任务验证失败 (第 {task.row_number} 行): {e}")
        
        result = {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "errors": errors,
        }
        
        logger.info(f"任务验证完成: 总计 {total}, 有效 {valid}, 无效 {invalid}")
        return result


def generate_template() -> str:
    """生成 CSV 模板内容
    
    Returns:
        CSV 模板字符串
    """
    lines = [
        "title,course_name,related_courses,related_teachers,category,tags,description,file_path",
        "2025年线性代数期中试卷,线性代数,线性代数I;线性代数II,张三;李四,past_paper,期中;2025;试卷,2025年春季学期期中考试试卷（含答案）,/path/to/exam1.pdf",
        "微积分复习笔记,微积分,微积分上;微积分下,王五,note,复习;笔记;总结,第一章到第五章重点整理,/path/to/notes.md",
        "计算机组成原理讲义,计算机组成原理,计算机组成原理,赵六,lecture,讲义;PPT,2025年春季课程讲义,/path/to/lecture.pptx",
    ]
    return "\n".join(lines)


def print_csv_help():
    """打印 CSV 格式帮助信息"""
    help_text = """
CSV 文件格式说明:
================

必需字段:
  title       - 资源标题
  category    - 资源分类 (past_paper/note/review_outline/lecture/exam_result/learning_note/other)
  file_path   - 本地文件路径

可选字段:
  course_name       - 适用课程名称（自由文本）
  related_courses   - 关联课程（分号分隔，如"课程A;课程B"）
  related_teachers  - 关联教师（分号分隔，如"张老师;李老师"）
  tags              - 标签（分号分隔，如"期中;2025;试卷"）
  description       - 资源描述

示例 CSV:
---------
title,course_name,related_courses,related_teachers,category,tags,description,file_path
2025年线性代数期中试卷,线性代数,线性代数I;线性代数II,张三;李四,past_paper,期中;2025;试卷,2025年春季期中试卷,/path/to/exam.pdf

提示:
  - 文件必须是 UTF-8 编码
  - 文件路径可以是相对路径或绝对路径
  - 支持的分隔符: 逗号(,)、分号(;)、中文分号(；)
"""
    print(help_text)
