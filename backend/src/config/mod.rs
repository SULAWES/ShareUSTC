use std::env;

/// OSS 配置结构体
#[derive(Clone, Debug)]
pub struct OssConfig {
    pub access_key_id: String,
    pub access_key_secret: String,
    pub bucket: String,
    pub region: String,
    pub endpoint: String,
    pub public_url: String,
    pub sts_role_arn: String,
    pub sts_session_duration: u64,
}

impl OssConfig {
    /// 从环境变量加载 OSS 配置
    pub fn from_env() -> Self {
        Self {
            access_key_id: env::var("ALIYUN_ACCESS_KEY_ID").unwrap_or_default(),
            access_key_secret: env::var("ALIYUN_ACCESS_KEY_SECRET").unwrap_or_default(),
            bucket: env::var("OSS_BUCKET").unwrap_or_default(),
            region: env::var("OSS_REGION").unwrap_or_else(|_| "oss-cn-shanghai".to_string()),
            endpoint: env::var("OSS_ENDPOINT")
                .unwrap_or_else(|_| "https://oss-cn-shanghai.aliyuncs.com".to_string()),
            public_url: env::var("OSS_PUBLIC_URL").unwrap_or_default(),
            sts_role_arn: env::var("STS_ROLE_ARN").unwrap_or_default(),
            sts_session_duration: env::var("STS_SESSION_DURATION")
                .ok()
                .and_then(|s| s.parse().ok())
                .unwrap_or(900),
        }
    }

    /// 是否已设置必要的 OSS 配置
    pub fn is_configured(&self) -> bool {
        !self.access_key_id.is_empty()
            && !self.access_key_secret.is_empty()
            && !self.bucket.is_empty()
            && !self.sts_role_arn.is_empty()
    }
}

/// 应用配置结构体
#[derive(Clone, Debug)]
pub struct Config {
    pub database_url: String,
    pub jwt_secret: String,
    pub server_host: String,
    pub server_port: u16,
    pub log_level: String,
    pub image_upload_path: String,
    pub resource_upload_path: String,
    pub oss: OssConfig,
}

impl Config {
    /// 从环境变量加载配置
    pub fn from_env() -> Self {
        Self {
            database_url: env::var("DATABASE_URL")
                .unwrap_or_else(|_| "postgres://postgres:postgres@localhost/shareustc".to_string()),
            jwt_secret: env::var("JWT_SECRET").unwrap_or_else(|_| "your-secret-key".to_string()),
            server_host: env::var("SERVER_HOST").unwrap_or_else(|_| "127.0.0.1".to_string()),
            server_port: env::var("SERVER_PORT")
                .ok()
                .and_then(|p| p.parse().ok())
                .unwrap_or(8080),
            log_level: env::var("RUST_LOG")
                .unwrap_or_else(|_| "backend=debug,actix_web=info,sqlx=warn".to_string()),
            image_upload_path: env::var("IMAGE_UPLOAD_PATH")
                .unwrap_or_else(|_| "./uploads/images".to_string()),
            resource_upload_path: env::var("RESOURCE_UPLOAD_PATH")
                .unwrap_or_else(|_| "./uploads/resources".to_string()),
            oss: OssConfig::from_env(),
        }
    }
}
