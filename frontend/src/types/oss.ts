export type OssUploadPrefix = 'resources' | 'images';

export interface StsTokenResponse {
  accessKeyId: string;
  accessKeySecret: string;
  securityToken: string;
  expiration: string;
  bucket: string;
  region: string;
  endpoint: string;
}

export interface OssUploadResult {
  ossKey: string;
  fileName: string;
  fileSize: number;
  mimeType?: string;
}

