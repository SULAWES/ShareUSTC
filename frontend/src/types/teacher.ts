// 授课教师类型定义

/**
 * 授课教师
 */
export interface Teacher {
  sn: number;
  name: string;
  department?: string;
  isActive: boolean;
}

/**
 * 教师列表项（用于管理员列表）
 */
export interface TeacherListItem {
  id: string;
  sn: number;
  name: string;
  department?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

/**
 * 教师列表响应
 */
export interface TeacherListResponse {
  teachers: TeacherListItem[];
  total: number;
  page: number;
  perPage: number;
}

/**
 * 创建教师请求
 */
export interface CreateTeacherRequest {
  name: string;
  department?: string;
}

/**
 * 更新教师请求
 */
export interface UpdateTeacherRequest {
  name?: string;
  department?: string;
}

/**
 * 更新教师状态请求
 */
export interface UpdateTeacherStatusRequest {
  isActive: boolean;
}

/**
 * 教师列表查询参数
 */
export interface TeacherListQuery {
  page?: number;
  perPage?: number;
  department?: string;
  isActive?: boolean;
}
