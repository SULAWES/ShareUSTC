import request from './request';
import type { OssUploadPrefix, StsTokenResponse } from '../types/oss';

export const getStsToken = async (prefix: OssUploadPrefix): Promise<StsTokenResponse> => {
  return request({
    url: '/oss/sts-token',
    method: 'post',
    data: { prefix }
  }) as Promise<StsTokenResponse>;
};

