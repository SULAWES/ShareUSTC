"""智能匹配模块

将用户输入的课程名称和教师名称匹配到系统中的编号(sn)。
支持精确匹配和交互式模糊匹配选择。
"""

import logging
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING, Union
from dataclasses import dataclass
from difflib import SequenceMatcher

import requests

if TYPE_CHECKING:
    from csv_parser import UploadTask

logger = logging.getLogger("shareustc_upload")


@dataclass
class Entity:
    """实体（课程或教师）"""
    sn: int
    name: str
    extra: Optional[str] = None  # 额外信息（如课程学期、教师学院）
    
    def __str__(self) -> str:
        if self.extra:
            return f"{self.name} ({self.extra})"
        return self.name


class EntityMatcher:
    """实体匹配器

    负责将用户输入的名称匹配到系统中的实体编号。
    匹配策略：
    1. 精确匹配（完全相等）
    2. 如果精确匹配失败，计算所有实体的相似度，显示前5供用户选择
    """

    # 模糊匹配相似度阈值（最高相似度大于此值才显示候选项）
    SIMILARITY_THRESHOLD = 0.3

    # 显示的候选项数量
    TOP_MATCHES_COUNT = 5

    def __init__(self, base_url: str, session: requests.Session, cache_ttl: int = 3600):
        """初始化实体匹配器
        
        Args:
            base_url: API 基础 URL
            session: HTTP Session（已包含认证 Cookie）
            cache_ttl: 缓存时间（秒），默认 1 小时
        """
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.cache_ttl = cache_ttl
        
        # 缓存
        self._courses: Optional[List[Entity]] = None
        self._teachers: Optional[List[Entity]] = None
        
        logger.debug(f"EntityMatcher 初始化，base_url: {base_url}")
    
    def load_entities(self) -> bool:
        """加载课程和教师列表
        
        Returns:
            是否成功加载
        """
        logger.info("正在加载课程和教师列表...")
        
        courses_ok = self._load_courses()
        teachers_ok = self._load_teachers()
        
        if courses_ok:
            logger.info(f"已加载 {len(self._courses)} 个课程")
        else:
            logger.warning("加载课程列表失败")
        
        if teachers_ok:
            logger.info(f"已加载 {len(self._teachers)} 个教师")
        else:
            logger.warning("加载教师列表失败")
        
        return courses_ok or teachers_ok
    
    def _load_courses(self) -> bool:
        """加载课程列表"""
        try:
            url = f"{self.base_url}/api/courses"
            response = self.session.get(url, timeout=10)
            
            logger.debug(f"加载课程列表: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self._courses = []
                
                for item in data:
                    entity = Entity(
                        sn=item.get("sn", 0),
                        name=item.get("name", ""),
                        extra=item.get("semester")
                    )
                    if entity.sn and entity.name:
                        self._courses.append(entity)
                
                logger.debug("课程列表（前5个）:")
                for course in self._courses[:5]:
                    logger.debug(f"  - {course}")
                return True
            else:
                logger.error(f"加载课程列表失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"加载课程列表时发生错误: {e}")
            return False
    
    def _load_teachers(self) -> bool:
        """加载教师列表"""
        try:
            url = f"{self.base_url}/api/teachers"
            response = self.session.get(url, timeout=10)
            
            logger.debug(f"加载教师列表: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self._teachers = []
                
                for item in data:
                    entity = Entity(
                        sn=item.get("sn", 0),
                        name=item.get("name", ""),
                        extra=item.get("department")
                    )
                    if entity.sn and entity.name:
                        self._teachers.append(entity)
                
                logger.debug("教师列表（前5个）:")
                for teacher in self._teachers[:5]:
                    logger.debug(f"  - {teacher}")
                return True
            else:
                logger.error(f"加载教师列表失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"加载教师列表时发生错误: {e}")
            return False
    
    def _calculate_similarity(self, query: str, target: str) -> float:
        """计算两个字符串的相似度
        
        Args:
            query: 查询字符串
            target: 目标字符串
            
        Returns:
            相似度 (0.0 ~ 1.0)
        """
        return SequenceMatcher(None, query.lower(), target.lower()).ratio()
    
    def _find_top_matches(self, query: str, entities: List[Entity], top_n: int = 5) -> List[Tuple[float, Entity]]:
        """找出相似度最高的前 N 个实体
        
        Args:
            query: 查询字符串
            entities: 实体列表
            top_n: 返回数量
            
        Returns:
            [(相似度, 实体), ...] 按相似度降序排列
        """
        query = query.strip()
        
        # 计算所有实体的相似度
        scored = []
        for entity in entities:
            similarity = self._calculate_similarity(query, entity.name)
            scored.append((similarity, entity))
        
        # 按相似度降序排序
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # 返回前 N 个
        return scored[:top_n]
    
    SKIP_UPLOAD_MARKER = -999  # 特殊标记值，表示跳过整个资源上传

    def _interactive_select(self, query: str, candidates: List[Tuple[float, Entity]], entity_type: str) -> Union[List[int], int]:
        """交互式选择实体（支持多选）

        Args:
            query: 原始查询字符串
            candidates: [(相似度, 实体), ...]
            entity_type: 实体类型（"课程"或"教师"）

        Returns:
            - 选中的实体 SN 列表
            - 如果跳过关联则返回空列表
            - 如果跳过整个资源上传则返回 SKIP_UPLOAD_MARKER
        """
        from utils import print_info, print_warning

        print()
        print_warning(f"未找到精确匹配的{entity_type}: \"{query}\"")
        print_info(f"请选择最相似的{entity_type}（输入编号，多选用'-'分隔，如 2-3-5）：")
        print_info(f"  0 = 跳过关联 | s = 跳过此资源上传")
        print()

        # 显示候选项
        for i, (similarity, entity) in enumerate(candidates, 1):
            extra_info = f" ({entity.extra})" if entity.extra else ""
            bar = "█" * int(similarity * 10) + "░" * (10 - int(similarity * 10))
            print(f"  [{i}] {entity.name}{extra_info}")
            print(f"      相似度: {similarity:.2%} {bar}")
            print()

        print(f"  [0] 跳过此{entity_type}（不关联）")
        print(f"  [s] 跳过此资源上传（不上传此文件）")
        print()

        # 获取用户输入
        while True:
            try:
                choice = input(f"请选择 [0-{len(candidates)} 或 1-2-3, s]: ").strip().lower()

                if not choice:
                    print("  请输入有效选项")
                    continue

                if choice == 's':
                    print("  跳过此资源上传")
                    return self.SKIP_UPLOAD_MARKER

                if choice == '0':
                    print(f"  跳过此{entity_type}")
                    return []

                # 解析多选输入，如 "2-3-5"
                selected_indices = []
                valid = True
                for part in choice.split('-'):
                    try:
                        num = int(part.strip())
                        if 1 <= num <= len(candidates):
                            selected_indices.append(num)
                        else:
                            print(f"  编号 {num} 超出范围，请输入 1 到 {len(candidates)} 之间的数字")
                            valid = False
                            break
                    except ValueError:
                        print(f"  无效的输入: '{part}'，请输入数字或 's' 跳过上传")
                        valid = False
                        break

                if not valid:
                    continue

                if not selected_indices:
                    print("  请至少选择一个选项，或输入 0 跳过")
                    continue

                # 获取选中的实体 SN 列表（去重）
                selected_sns = []
                selected_names = []
                for idx in selected_indices:
                    entity = candidates[idx - 1][1]
                    if entity.sn not in selected_sns:
                        selected_sns.append(entity.sn)
                        selected_names.append(entity.name)

                print(f"  ✓ 已选择: {', '.join(selected_names)} (SN: {selected_sns})")
                return selected_sns

            except KeyboardInterrupt:
                print("\n  操作已取消")
                return []
    
    def match_course(self, course_name: str, interactive: bool = True) -> Union[List[int], int]:
        """匹配课程

        Args:
            course_name: 课程名称
            interactive: 是否启用交互式选择

        Returns:
            - 课程编号列表(sn list)，精确匹配返回单元素列表
            - 如果未匹配则返回空列表
            - 如果用户选择跳过上传则返回 SKIP_UPLOAD_MARKER
        """
        if not course_name or not self._courses:
            return []

        course_name = course_name.strip()
        logger.debug(f"匹配课程: {course_name}")

        # 1. 精确匹配（完全相等）
        for course in self._courses:
            if course.name == course_name:
                logger.debug(f"课程精确匹配成功: {course_name} -> SN {course.sn}")
                return [course.sn]

        # 2. 精确匹配失败，显示前5相似度供选择
        if interactive:
            top_matches = self._find_top_matches(course_name, self._courses, top_n=self.TOP_MATCHES_COUNT)

            if top_matches and top_matches[0][0] > self.SIMILARITY_THRESHOLD:  # 最高相似度大于阈值才显示
                result = self._interactive_select(course_name, top_matches, "课程")
                return result

        logger.warning(f"未找到匹配的课程: {course_name}")
        return []

    def match_teacher(self, teacher_name: str, interactive: bool = True) -> Union[List[int], int]:
        """匹配教师

        Args:
            teacher_name: 教师名称
            interactive: 是否启用交互式选择

        Returns:
            - 教师编号列表(sn list)，精确匹配返回单元素列表
            - 如果未匹配则返回空列表
            - 如果用户选择跳过上传则返回 SKIP_UPLOAD_MARKER
        """
        if not teacher_name or not self._teachers:
            return None
        
        teacher_name = teacher_name.strip()
        logger.debug(f"匹配教师: {teacher_name}")
        
        # 1. 精确匹配（完全相等）
        for teacher in self._teachers:
            if teacher.name == teacher_name:
                logger.debug(f"教师精确匹配成功: {teacher_name} -> SN {teacher.sn}")
                return [teacher.sn]

        # 2. 精确匹配失败，显示前5相似度供选择
        if interactive:
            top_matches = self._find_top_matches(teacher_name, self._teachers, top_n=self.TOP_MATCHES_COUNT)

            if top_matches and top_matches[0][0] > self.SIMILARITY_THRESHOLD:  # 最高相似度大于阈值才显示
                result = self._interactive_select(teacher_name, top_matches, "教师")
                return result

        logger.warning(f"未找到匹配的教师: {teacher_name}")
        return []
    
    def match_courses(self, course_names: List[str], interactive: bool = True) -> Tuple[List[int], List[str], bool]:
        """批量匹配课程（结果取并集）

        Args:
            course_names: 课程名称列表
            interactive: 是否启用交互式选择

        Returns:
            (匹配的编号列表(去重并集), 未匹配的名称列表, 是否跳过上传)
            如果用户选择跳过上传，第三个元素为 True
        """
        matched_set = set()
        unmatched = []

        for name in course_names:
            result = self.match_course(name, interactive=interactive)
            if result == self.SKIP_UPLOAD_MARKER:
                # 用户选择跳过整个上传
                return [], [], True
            if isinstance(result, list) and result:
                matched_set.update(result)
            elif not result:
                unmatched.append(name)

        return sorted(list(matched_set)), unmatched, False

    def match_teachers(self, teacher_names: List[str], interactive: bool = True) -> Tuple[List[int], List[str], bool]:
        """批量匹配教师（结果取并集）

        Args:
            teacher_names: 教师名称列表
            interactive: 是否启用交互式选择

        Returns:
            (匹配的编号列表(去重并集), 未匹配的名称列表, 是否跳过上传)
            如果用户选择跳过上传，第三个元素为 True
        """
        matched_set = set()
        unmatched = []

        for name in teacher_names:
            result = self.match_teacher(name, interactive=interactive)
            if result == self.SKIP_UPLOAD_MARKER:
                # 用户选择跳过整个上传
                return [], [], True
            if isinstance(result, list) and result:
                matched_set.update(result)
            elif not result:
                unmatched.append(name)

        return sorted(list(matched_set)), unmatched, False


def match_task_entities(task: "UploadTask", matcher: EntityMatcher, interactive: bool = True) -> Tuple[List[str], List[str], bool]:
    """匹配任务中的实体

    Args:
        task: 上传任务
        matcher: 实体匹配器
        interactive: 是否启用交互式选择

    Returns:
        (警告列表, 错误列表, 是否继续上传)
        如果用户选择跳过上传，第三个元素为 False
    """
    warnings = []
    errors = []

    # 匹配课程
    if task.related_courses:
        print(f"\n正在匹配课程（任务: {task.title}）...")
        matched_sns, unmatched, skip_upload = matcher.match_courses(task.related_courses, interactive=interactive)

        if skip_upload:
            print(f"  跳过上传: {task.title}")
            return warnings, errors, False

        task.matched_course_sns = matched_sns

        if unmatched:
            warnings.append(f"以下课程未关联: {', '.join(unmatched)}")
            logger.warning(f"任务 '{task.title}' 中未关联的课程: {unmatched}")

        logger.debug(f"课程匹配结果: {task.related_courses} -> SNs {matched_sns}")

    # 匹配教师
    if task.related_teachers:
        print(f"\n正在匹配教师（任务: {task.title}）...")
        matched_sns, unmatched, skip_upload = matcher.match_teachers(task.related_teachers, interactive=interactive)

        if skip_upload:
            print(f"  跳过上传: {task.title}")
            return warnings, errors, False

        task.matched_teacher_sns = matched_sns

        if unmatched:
            warnings.append(f"以下教师未关联: {', '.join(unmatched)}")
            logger.warning(f"任务 '{task.title}' 中未关联的教师: {unmatched}")

        logger.debug(f"教师匹配结果: {task.related_teachers} -> SNs {matched_sns}")

    return warnings, errors, True
