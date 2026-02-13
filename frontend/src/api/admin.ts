import request from './request';
import type {
  AdminCommentListResponse,
  AdminUserListResponse,
  DashboardStats,
  PendingResourceListResponse
} from '../types/admin';

/**
 * 管理员API封装
 */

// 仪表盘统计
export const getDashboardStats = async (): Promise<DashboardStats> => {
  return request({
    url: '/admin/dashboard',
    method: 'get'
  }) as Promise<DashboardStats>;
};

// 用户管理
export const getUserList = async (
  page: number = 1,
  perPage: number = 20
): Promise<AdminUserListResponse> => {
  return request({
    url: '/admin/users',
    method: 'get',
    params: { page, perPage }
  }) as Promise<AdminUserListResponse>;
};

export const updateUserStatus = async (
  userId: string,
  isActive: boolean
): Promise<void> => {
  return request({
    url: `/admin/users/${userId}/status`,
    method: 'put',
    data: { isActive }
  }) as Promise<void>;
};

// 资源审核
export const getPendingResources = async (
  page: number = 1,
  perPage: number = 20
): Promise<PendingResourceListResponse> => {
  return request({
    url: '/admin/resources/pending',
    method: 'get',
    params: { page, perPage }
  }) as Promise<PendingResourceListResponse>;
};

export const auditResource = async (
  resourceId: string,
  status: 'approved' | 'rejected',
  reason?: string
): Promise<void> => {
  return request({
    url: `/admin/resources/${resourceId}/audit`,
    method: 'put',
    data: { status, reason }
  }) as Promise<void>;
};

// 评论管理
export const getCommentList = (
  page: number = 1,
  perPage: number = 20,
  auditStatus?: string
): Promise<AdminCommentListResponse> => {
  const params: Record<string, string | number> = { page, perPage };
  if (auditStatus) {
    params.auditStatus = auditStatus;
  }
  return request({
    url: '/admin/comments',
    method: 'get',
    params
  }) as Promise<AdminCommentListResponse>;
};

export const deleteComment = async (commentId: string): Promise<void> => {
  return request({
    url: `/admin/comments/${commentId}`,
    method: 'delete'
  }) as Promise<void>;
};

export const auditComment = async (
  commentId: string,
  status: 'approved' | 'rejected'
): Promise<void> => {
  return request({
    url: `/admin/comments/${commentId}/audit`,
    method: 'put',
    data: { status }
  }) as Promise<void>;
};

// 导出API对象
export const adminApi = {
  getDashboardStats,
  getUserList,
  updateUserStatus,
  getPendingResources,
  auditResource,
  getCommentList,
  deleteComment,
  auditComment
};
