import request from './request';
import type { Course } from '@/types/course';

/**
 * 获取有效课程列表（公开）
 */
export const getCourses = (): Promise<Course[]> => {
  return request.get('/courses');
};

/**
 * 课程 API 对象
 */
export const courseApi = {
  getCourses,
};
