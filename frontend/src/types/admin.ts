export interface DashboardStats {
  totalUsers: number;
  totalResources: number;
  totalDownloads: number;
  pendingResources: number;
  pendingComments: number;
  todayNewUsers: number;
  todayNewResources: number;
}

export interface AdminUserListItem {
  id: string;
  username: string;
  email: string | null;
  role: string;
  isVerified: boolean;
  isActive: boolean;
  createdAt: string;
}

export interface AdminUserListResponse {
  users: AdminUserListItem[];
  total: number;
  page: number;
  perPage: number;
}

export interface PendingResourceItem {
  id: string;
  title: string;
  courseName: string | null;
  resourceType: string;
  category: string;
  uploaderId: string;
  uploaderName: string | null;
  aiRejectReason: string | null;
  createdAt: string;
}

export interface PendingResourceListResponse {
  resources: PendingResourceItem[];
  total: number;
  page: number;
  perPage: number;
}

export interface AdminCommentItem {
  id: string;
  resourceId: string;
  resourceTitle: string | null;
  userId: string;
  userName: string | null;
  content: string;
  auditStatus: string;
  createdAt: string;
}

export interface AdminCommentListResponse {
  comments: AdminCommentItem[];
  total: number;
  page: number;
  perPage: number;
}

