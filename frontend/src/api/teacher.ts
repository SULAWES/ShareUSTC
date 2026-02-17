import request from './request';
import type { Teacher } from '@/types/teacher';

/**
 * 获取有效教师列表（公开）
 */
export const getTeachers = (): Promise<Teacher[]> => {
  return request.get('/teachers');
};

/**
 * 教师 API 对象
 */
export const teacherApi = {
  getTeachers,
};
