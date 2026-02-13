import request from './request';
import type {
  ResourceListResponse,
  ResourceListQuery,
  ResourceSearchQuery,
  ResourceDetail,
  UploadResourceRequest,
  UploadResourceResponse,
  ConfirmResourceUploadRequest
} from '../types/resource';

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T | null;
}

interface ResourceDownloadUrlData {
  downloadUrl: string;
  fileName: string;
  expiresIn: number;
}

interface ResourceContentUrlData {
  contentUrl: string;
  resourceType: string;
  expiresIn: number;
}

const getBaseUrl = (): string => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api';
  return baseUrl.replace(/\/api$/, '');
};

const getAuthHeaders = (): HeadersInit => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    return {};
  }
  return {
    Authorization: `Bearer ${token}`
  };
};

const isJsonResponse = (response: Response): boolean => {
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('application/json');
};

const parseApiResponse = async <T>(response: Response): Promise<T> => {
  const payload = await response.json() as ApiResponse<T>;
  if (payload.code !== 200) {
    throw new Error(payload.message || '请求失败');
  }
  if (payload.data === null) {
    throw new Error(payload.message || '响应数据为空');
  }
  return payload.data;
};

/**
 * 获取资源列表
 * @param params 查询参数
 * @returns 资源列表
 */
export const getResourceList = async (params?: ResourceListQuery): Promise<ResourceListResponse> => {
  return request({
    url: '/resources',
    method: 'get',
    params
  }) as Promise<ResourceListResponse>;
};

/**
 * 搜索资源
 * @param params 搜索参数
 * @returns 搜索结果
 */
export const searchResources = async (params: ResourceSearchQuery): Promise<ResourceListResponse> => {
  return request({
    url: '/resources/search',
    method: 'get',
    params
  }) as Promise<ResourceListResponse>;
};

/**
 * 获取资源详情
 * @param resourceId 资源ID
 * @returns 资源详情
 */
export const getResourceDetail = async (resourceId: string): Promise<ResourceDetail> => {
  return request({
    url: `/resources/${resourceId}`,
    method: 'get'
  }) as Promise<ResourceDetail>;
};

/**
 * 获取我的资源列表
 * @param params 查询参数
 * @returns 资源列表
 */
export const getMyResources = async (params?: ResourceListQuery): Promise<ResourceListResponse> => {
  return request({
    url: '/resources/my',
    method: 'get',
    params
  }) as Promise<ResourceListResponse>;
};

/**
 * 上传资源
 * @param metadata 资源元数据
 * @param file 文件
 * @param onProgress 进度回调
 * @returns 上传结果
 */
export const uploadResource = async (
  metadata: UploadResourceRequest,
  file: File,
  onProgress?: (percent: number) => void
): Promise<UploadResourceResponse> => {
  const formData = new FormData();

  // 添加元数据
  formData.append('metadata', new Blob([JSON.stringify(metadata)], { type: 'application/json' }));

  // 添加文件
  formData.append('file', file);

  return request({
    url: '/resources',
    method: 'post',
    data: formData,
    timeout: 120000, // 文件上传需要更长的超时时间（2分钟）
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    }
  }) as Promise<UploadResourceResponse>;
};

/**
 * 确认 OSS 上传资源
 * @param payload OSS 上传确认数据
 * @returns 上传结果
 */
export const confirmUpload = async (
  payload: ConfirmResourceUploadRequest
): Promise<UploadResourceResponse> => {
  return request({
    url: '/resources/confirm',
    method: 'post',
    data: payload
  }) as Promise<UploadResourceResponse>;
};

/**
 * 删除资源
 * @param resourceId 资源ID
 */
export const deleteResource = async (resourceId: string): Promise<void> => {
  return request({
    url: `/resources/${resourceId}`,
    method: 'delete'
  }) as Promise<void>;
};

/**
 * 下载资源
 * @param resourceId 资源ID
 * @param fileName 文件名
 */
export const downloadResource = async (resourceId: string, fileName?: string): Promise<void> => {
  try {
    const response = await fetch(
      `${getBaseUrl()}/api/resources/${resourceId}/download`,
      {
        headers: getAuthHeaders()
      }
    );

    if (!response.ok) {
      throw new Error(`下载失败 (${response.status})`);
    }

    // OSS 场景：返回 JSON，包含签名 URL
    if (isJsonResponse(response)) {
      const data = await parseApiResponse<ResourceDownloadUrlData>(response);
      const link = document.createElement('a');
      link.href = data.downloadUrl;
      link.target = '_blank';
      link.rel = 'noopener';
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      return;
    }

    // 获取文件名
    const contentDisposition = response.headers.get('content-disposition');
    let downloadFileName = fileName || 'download';
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match && match[1]) {
        downloadFileName = match[1];
      }
    }

    // 创建下载链接
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = downloadFileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('下载失败:', error);
    throw error;
  }
};

/**
 * 获取资源预览URL
 * @param resourceId 资源ID
 * @returns 预览URL
 */
export const getResourcePreviewUrl = (resourceId: string): string => {
  return `${getBaseUrl()}/api/resources/${resourceId}/content`;
};

/**
 * 获取资源文件内容（用于预览）
 * @param resourceId 资源ID
 * @returns Blob 文件内容
 */
export const getResourceContent = async (resourceId: string): Promise<Blob> => {
  const response = await fetch(
    `${getBaseUrl()}/api/resources/${resourceId}/content`,
    {
      headers: getAuthHeaders()
    }
  );

  if (!response.ok) {
    throw new Error(`获取资源内容失败 (${response.status})`);
  }

  // OSS 场景：先获取签名 URL，再请求真实文件内容
  if (isJsonResponse(response)) {
    const data = await parseApiResponse<ResourceContentUrlData>(response);
    const signedResponse = await fetch(data.contentUrl);
    if (!signedResponse.ok) {
      throw new Error(`获取预览内容失败 (${signedResponse.status})`);
    }
    const blob = await signedResponse.blob();
    return new Blob([blob], { type: blob.type || 'application/octet-stream' });
  }

  // 本地兼容场景：后端直接返回二进制
  const contentType = response.headers.get('content-type') || 'application/octet-stream';
  const blob = await response.blob();
  return new Blob([blob], { type: contentType });
};
