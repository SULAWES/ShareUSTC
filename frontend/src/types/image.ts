// 图片类型定义
// 注意：StorageType 和 StorageTypeLabels 在 resource.ts 中定义
// 请从 './resource' 导入这些类型

// 局部定义 StorageType 避免循环引用
type StorageType = 'local' | 'oss';

export interface Image {
  id: string;
  url: string;
  markdownLink: string;
  originalName?: string;
  fileSize?: number;
  mimeType?: string;
  createdAt: string;
  storageType: StorageType;
}

export interface ImageUploadResponse {
  id: string;
  url: string;
  markdownLink: string;
  originalName?: string;
  fileSize?: number;
  createdAt: string;
  storageType?: StorageType;
}

export interface ImageListResponse {
  images: Image[];
  total: number;
  page: number;
  perPage: number;
}

export interface ImageListQuery {
  page?: number;
  perPage?: number;
}
