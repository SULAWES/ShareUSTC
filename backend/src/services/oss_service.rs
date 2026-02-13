use crate::config::OssConfig;
use base64::{engine::general_purpose::STANDARD as BASE64_STANDARD, Engine};
use chrono::Utc;
use hmac::{Hmac, Mac};
use sha1::Sha1;
use std::collections::BTreeMap;
use uuid::Uuid;

type HmacSha1 = Hmac<Sha1>;

#[derive(Debug)]
pub enum OssError {
    ConfigError(String),
    ValidationError(String),
    RequestError(String),
    ServiceError(String),
    NotImplemented(String),
}

impl std::fmt::Display for OssError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OssError::ConfigError(msg) => write!(f, "配置错误: {}", msg),
            OssError::ValidationError(msg) => write!(f, "参数错误: {}", msg),
            OssError::RequestError(msg) => write!(f, "请求错误: {}", msg),
            OssError::ServiceError(msg) => write!(f, "服务错误: {}", msg),
            OssError::NotImplemented(msg) => write!(f, "未实现: {}", msg),
        }
    }
}

impl std::error::Error for OssError {}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct StsCredentials {
    pub access_key_id: String,
    pub access_key_secret: String,
    pub security_token: String,
    pub expiration: String,
}

pub struct OssService;

impl OssService {
    const STS_ENDPOINT: &'static str = "https://sts.aliyuncs.com/";

    /// 调用 STS AssumeRole，返回临时凭证
    pub async fn assume_role(
        config: &OssConfig,
        upload_prefix: &str,
    ) -> Result<StsCredentials, OssError> {
        Self::validate_config_for_sts(config)?;
        let prefix = Self::validate_upload_prefix(upload_prefix)?;

        let duration = config.sts_session_duration.clamp(900, 3600);
        let timestamp = Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();
        let nonce = Uuid::new_v4().to_string();
        let role_session_name = format!("shareustc-{}-{}", prefix, &nonce[..8]);
        let policy = Self::build_upload_policy(config, prefix);

        let mut params = BTreeMap::new();
        params.insert("AccessKeyId".to_string(), config.access_key_id.clone());
        params.insert("Action".to_string(), "AssumeRole".to_string());
        params.insert("Format".to_string(), "JSON".to_string());
        params.insert("Version".to_string(), "2015-04-01".to_string());
        params.insert("SignatureMethod".to_string(), "HMAC-SHA1".to_string());
        params.insert("Timestamp".to_string(), timestamp);
        params.insert("SignatureVersion".to_string(), "1.0".to_string());
        params.insert("SignatureNonce".to_string(), nonce);
        params.insert("RoleArn".to_string(), config.sts_role_arn.clone());
        params.insert("RoleSessionName".to_string(), role_session_name);
        params.insert("DurationSeconds".to_string(), duration.to_string());
        params.insert("Policy".to_string(), policy);

        let canonical_query = Self::canonicalize_query(&params);
        let string_to_sign = format!("GET&%2F&{}", Self::aliyun_percent_encode(&canonical_query));
        let signature = Self::sign_sts_request(&config.access_key_secret, &string_to_sign)?;

        params.insert("Signature".to_string(), signature);
        let final_query = Self::canonicalize_query(&params);
        let request_url = format!(
            "{}?{}",
            Self::STS_ENDPOINT.trim_end_matches('/'),
            final_query
        );

        let response = reqwest::Client::new()
            .get(request_url)
            .send()
            .await
            .map_err(|e| OssError::RequestError(format!("STS 请求失败: {}", e)))?;

        let status = response.status();
        let body = response
            .text()
            .await
            .map_err(|e| OssError::RequestError(format!("读取 STS 响应失败: {}", e)))?;

        if !status.is_success() {
            let service_error = serde_json::from_str::<StsErrorResponse>(&body).ok();
            let code = service_error
                .as_ref()
                .and_then(|v| v.code.clone())
                .unwrap_or_else(|| status.as_u16().to_string());
            let message = service_error
                .as_ref()
                .and_then(|v| v.message.clone())
                .unwrap_or_else(|| "STS 服务返回异常".to_string());
            return Err(OssError::ServiceError(format!("{}: {}", code, message)));
        }

        let parsed: StsSuccessResponse = serde_json::from_str(&body).map_err(|e| {
            OssError::ServiceError(format!("解析 STS 响应失败: {}，响应: {}", e, body))
        })?;

        Ok(StsCredentials {
            access_key_id: parsed.credentials.access_key_id,
            access_key_secret: parsed.credentials.access_key_secret,
            security_token: parsed.credentials.security_token,
            expiration: parsed.credentials.expiration,
        })
    }

    /// 生成签名 URL（用于下载/预览私有文件）
    pub fn generate_presigned_url(
        config: &OssConfig,
        object_key: &str,
        expires_secs: u64,
    ) -> Result<String, OssError> {
        Self::validate_config_for_sign(config)?;

        if object_key.trim().is_empty() {
            return Err(OssError::ValidationError("object_key 不能为空".to_string()));
        }

        if expires_secs == 0 {
            return Err(OssError::ValidationError(
                "expires_secs 必须大于 0".to_string(),
            ));
        }

        let object_key = object_key.trim().trim_start_matches('/');
        let expires = (Utc::now().timestamp() + expires_secs as i64).to_string();

        let string_to_sign = format!("GET\n\n\n{}\n/{}/{}", expires, config.bucket, object_key);
        let signature = Self::sign_oss_request(&config.access_key_secret, &string_to_sign)?;
        let endpoint = Self::build_oss_base_url(config);

        Ok(format!(
            "{}/{}?OSSAccessKeyId={}&Expires={}&Signature={}",
            endpoint,
            object_key,
            Self::aliyun_percent_encode(&config.access_key_id),
            Self::aliyun_percent_encode(&expires),
            Self::aliyun_percent_encode(&signature),
        ))
    }

    /// 删除 OSS 对象
    pub async fn delete_object(config: &OssConfig, object_key: &str) -> Result<(), OssError> {
        Self::validate_config_for_sign(config)?;

        if object_key.trim().is_empty() {
            return Err(OssError::ValidationError("object_key 不能为空".to_string()));
        }

        let object_key = object_key.trim().trim_start_matches('/');
        let expires = (Utc::now().timestamp() + 300).to_string();
        let string_to_sign = format!("DELETE\n\n\n{}\n/{}/{}", expires, config.bucket, object_key);
        let signature = Self::sign_oss_request(&config.access_key_secret, &string_to_sign)?;
        let endpoint = Self::build_oss_base_url(config);

        let delete_url = format!(
            "{}/{}?OSSAccessKeyId={}&Expires={}&Signature={}",
            endpoint,
            object_key,
            Self::aliyun_percent_encode(&config.access_key_id),
            Self::aliyun_percent_encode(&expires),
            Self::aliyun_percent_encode(&signature),
        );

        let response = reqwest::Client::new()
            .delete(delete_url)
            .send()
            .await
            .map_err(|e| OssError::RequestError(format!("OSS 删除请求失败: {}", e)))?;

        let status = response.status();
        if status.is_success() || status.as_u16() == 404 {
            return Ok(());
        }

        let body = response
            .text()
            .await
            .unwrap_or_else(|_| "读取响应失败".to_string());
        Err(OssError::ServiceError(format!(
            "OSS 删除失败: status={}, body={}",
            status, body
        )))
    }

    fn validate_config_for_sts(config: &OssConfig) -> Result<(), OssError> {
        if config.access_key_id.trim().is_empty() {
            return Err(OssError::ConfigError(
                "ALIYUN_ACCESS_KEY_ID 未配置".to_string(),
            ));
        }
        if config.access_key_secret.trim().is_empty() {
            return Err(OssError::ConfigError(
                "ALIYUN_ACCESS_KEY_SECRET 未配置".to_string(),
            ));
        }
        if config.sts_role_arn.trim().is_empty() {
            return Err(OssError::ConfigError("STS_ROLE_ARN 未配置".to_string()));
        }
        if config.bucket.trim().is_empty() {
            return Err(OssError::ConfigError("OSS_BUCKET 未配置".to_string()));
        }
        Ok(())
    }

    fn validate_config_for_sign(config: &OssConfig) -> Result<(), OssError> {
        if config.access_key_id.trim().is_empty() {
            return Err(OssError::ConfigError(
                "ALIYUN_ACCESS_KEY_ID 未配置".to_string(),
            ));
        }
        if config.access_key_secret.trim().is_empty() {
            return Err(OssError::ConfigError(
                "ALIYUN_ACCESS_KEY_SECRET 未配置".to_string(),
            ));
        }
        if config.bucket.trim().is_empty() {
            return Err(OssError::ConfigError("OSS_BUCKET 未配置".to_string()));
        }
        Ok(())
    }

    fn validate_upload_prefix(upload_prefix: &str) -> Result<&str, OssError> {
        match upload_prefix {
            "resources" | "images" => Ok(upload_prefix),
            _ => Err(OssError::ValidationError(
                "prefix 仅允许 resources 或 images".to_string(),
            )),
        }
    }

    fn build_upload_policy(config: &OssConfig, upload_prefix: &str) -> String {
        serde_json::json!({
            "Version": "1",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "oss:PutObject",
                    "oss:InitiateMultipartUpload",
                    "oss:UploadPart",
                    "oss:CompleteMultipartUpload",
                    "oss:AbortMultipartUpload",
                    "oss:ListParts"
                ],
                "Resource": [
                    format!("acs:oss:*:*:{}/{}/{}", config.bucket, upload_prefix, "*")
                ]
            }]
        })
        .to_string()
    }

    fn sign_sts_request(access_key_secret: &str, string_to_sign: &str) -> Result<String, OssError> {
        let signing_key = format!("{}&", access_key_secret);
        let mut mac = HmacSha1::new_from_slice(signing_key.as_bytes())
            .map_err(|e| OssError::ConfigError(format!("初始化签名器失败: {}", e)))?;
        mac.update(string_to_sign.as_bytes());
        Ok(BASE64_STANDARD.encode(mac.finalize().into_bytes()))
    }

    fn sign_oss_request(access_key_secret: &str, string_to_sign: &str) -> Result<String, OssError> {
        let mut mac = HmacSha1::new_from_slice(access_key_secret.as_bytes())
            .map_err(|e| OssError::ConfigError(format!("初始化签名器失败: {}", e)))?;
        mac.update(string_to_sign.as_bytes());
        Ok(BASE64_STANDARD.encode(mac.finalize().into_bytes()))
    }

    fn canonicalize_query(params: &BTreeMap<String, String>) -> String {
        params
            .iter()
            .map(|(k, v)| {
                format!(
                    "{}={}",
                    Self::aliyun_percent_encode(k),
                    Self::aliyun_percent_encode(v)
                )
            })
            .collect::<Vec<_>>()
            .join("&")
    }

    fn aliyun_percent_encode(input: &str) -> String {
        let mut encoded = String::with_capacity(input.len());
        for byte in input.bytes() {
            match byte {
                b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                    encoded.push(byte as char)
                }
                _ => encoded.push_str(&format!("%{:02X}", byte)),
            }
        }
        encoded
    }

    fn build_oss_base_url(config: &OssConfig) -> String {
        if !config.public_url.trim().is_empty() {
            return config.public_url.trim_end_matches('/').to_string();
        }

        let endpoint = config
            .endpoint
            .trim()
            .trim_start_matches("https://")
            .trim_start_matches("http://")
            .trim_end_matches('/');
        format!("https://{}.{}", config.bucket, endpoint)
    }
}

#[derive(Debug, serde::Deserialize)]
struct StsSuccessResponse {
    #[serde(rename = "Credentials")]
    credentials: StsSuccessCredentials,
}

#[derive(Debug, serde::Deserialize)]
struct StsSuccessCredentials {
    #[serde(rename = "AccessKeyId")]
    access_key_id: String,
    #[serde(rename = "AccessKeySecret")]
    access_key_secret: String,
    #[serde(rename = "SecurityToken")]
    security_token: String,
    #[serde(rename = "Expiration")]
    expiration: String,
}

#[derive(Debug, serde::Deserialize)]
struct StsErrorResponse {
    #[serde(rename = "Code")]
    code: Option<String>,
    #[serde(rename = "Message")]
    message: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mock_config() -> OssConfig {
        OssConfig {
            access_key_id: "ak".to_string(),
            access_key_secret: "sk".to_string(),
            bucket: "shareustc-test".to_string(),
            region: "oss-cn-shanghai".to_string(),
            endpoint: "https://oss-cn-shanghai.aliyuncs.com".to_string(),
            public_url: "https://shareustc-test.oss-cn-shanghai.aliyuncs.com".to_string(),
            sts_role_arn: "acs:ram::123:role/test".to_string(),
            sts_session_duration: 900,
        }
    }

    #[test]
    fn test_validate_prefix() {
        assert!(OssService::validate_upload_prefix("resources").is_ok());
        assert!(OssService::validate_upload_prefix("images").is_ok());
        assert!(OssService::validate_upload_prefix("other").is_err());
    }

    #[test]
    fn test_generate_presigned_url_validation() {
        let config = mock_config();
        let result = OssService::generate_presigned_url(&config, "", 1800);
        assert!(result.is_err());
    }

    #[test]
    fn test_generate_presigned_url_success() {
        let config = mock_config();
        let result = OssService::generate_presigned_url(&config, "resources/test.pdf", 1800);
        assert!(result.is_ok());
        let url = result.unwrap();
        assert!(url.contains("resources/test.pdf"));
        assert!(url.contains("OSSAccessKeyId="));
        assert!(url.contains("Signature="));
    }

    #[test]
    fn test_build_upload_policy_contains_prefix_and_bucket() {
        let config = mock_config();
        let policy = OssService::build_upload_policy(&config, "resources");
        assert!(policy.contains("shareustc-test"));
        assert!(policy.contains("resources"));
    }

    #[test]
    fn test_percent_encode() {
        let encoded = OssService::aliyun_percent_encode("a b*c~");
        assert_eq!(encoded, "a%20b%2Ac~");
    }
}
