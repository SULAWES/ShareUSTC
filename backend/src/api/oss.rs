use actix_web::{post, web, HttpResponse, Responder};

use crate::db::AppState;
use crate::models::CurrentUser;
use crate::services::{OssError, OssService};

#[derive(Debug, serde::Deserialize)]
pub struct StsTokenRequest {
    pub prefix: String,
}

#[derive(Debug, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct StsTokenResponseData {
    pub access_key_id: String,
    pub access_key_secret: String,
    pub security_token: String,
    pub expiration: String,
    pub bucket: String,
    pub region: String,
    pub endpoint: String,
}

/// 获取 OSS STS 临时凭证
#[post("/oss/sts-token")]
pub async fn get_sts_token(
    state: web::Data<AppState>,
    user: web::ReqData<CurrentUser>,
    req: web::Json<StsTokenRequest>,
) -> impl Responder {
    let request = req.into_inner();

    log::info!(
        "用户请求 STS 凭证: user_id={}, prefix={}",
        user.id,
        request.prefix
    );

    match OssService::assume_role(&state.oss_config, request.prefix.as_str()).await {
        Ok(credentials) => {
            let response = StsTokenResponseData {
                access_key_id: credentials.access_key_id,
                access_key_secret: credentials.access_key_secret,
                security_token: credentials.security_token,
                expiration: credentials.expiration,
                bucket: state.oss_config.bucket.clone(),
                region: state.oss_config.region.clone(),
                endpoint: state.oss_config.endpoint.clone(),
            };

            HttpResponse::Ok().json(serde_json::json!({
                "code": 200,
                "message": "获取 STS 凭证成功",
                "data": response
            }))
        }
        Err(err) => {
            log::warn!("获取 STS 凭证失败: {}", err);
            let (code, message) = map_oss_error(err);

            HttpResponse::Ok().json(serde_json::json!({
                "code": code,
                "message": message,
                "data": null
            }))
        }
    }
}

fn map_oss_error(err: OssError) -> (i32, String) {
    match err {
        OssError::ValidationError(msg) => (400, msg),
        OssError::ConfigError(msg) => (500, msg),
        OssError::RequestError(msg) => (502, msg),
        OssError::ServiceError(msg) => (502, msg),
        OssError::NotImplemented(msg) => (501, msg),
    }
}

pub fn config(cfg: &mut web::ServiceConfig) {
    cfg.service(get_sts_token);
}
