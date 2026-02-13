import OSS from 'ali-oss';
import { getStsToken } from '../api/oss';
import type { OssUploadPrefix, OssUploadResult } from '../types/oss';

interface OssUploadOptions {
  file: File;
  prefix: OssUploadPrefix;
  onProgress?: (percent: number) => void;
}

function normalizeEndpoint(endpoint: string): { endpoint: string; secure: boolean } {
  const trimmed = endpoint.trim();
  if (trimmed.startsWith('https://')) {
    return { endpoint: trimmed.replace(/^https:\/\//, ''), secure: true };
  }
  if (trimmed.startsWith('http://')) {
    return { endpoint: trimmed.replace(/^http:\/\//, ''), secure: false };
  }
  return { endpoint: trimmed, secure: true };
}

export const ossUpload = async (options: OssUploadOptions): Promise<OssUploadResult> => {
  const { file, prefix, onProgress } = options;

  const sts = await getStsToken(prefix);
  const endpointConfig = normalizeEndpoint(sts.endpoint);

  const client = new OSS({
    region: sts.region,
    bucket: sts.bucket,
    endpoint: endpointConfig.endpoint,
    secure: endpointConfig.secure,
    accessKeyId: sts.accessKeyId,
    accessKeySecret: sts.accessKeySecret,
    stsToken: sts.securityToken
  });

  const ext = file.name.split('.').pop()?.toLowerCase() || 'bin';
  const ossKey = `${prefix}/${crypto.randomUUID()}.${ext}`;

  if (file.size < 5 * 1024 * 1024) {
    await client.put(ossKey, file);
    onProgress?.(100);
  } else {
    await client.multipartUpload(ossKey, file, {
      progress: async (progress: number) => {
        onProgress?.(Math.round(progress * 100));
      }
    });
  }

  return {
    ossKey,
    fileName: file.name,
    fileSize: file.size,
    mimeType: file.type || undefined
  };
};

