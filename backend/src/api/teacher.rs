use actix_web::{get, web, HttpResponse, Responder};

use crate::db::AppState;
use crate::services::{TeacherError, TeacherService};
use crate::utils::internal_error;

/// 将 TeacherError 转换为 HttpResponse
fn handle_teacher_error(err: TeacherError) -> HttpResponse {
    match err {
        TeacherError::NotFound(msg) => HttpResponse::NotFound().json(serde_json::json!({
            "error": msg
        })),
        TeacherError::ValidationError(msg) => HttpResponse::BadRequest().json(serde_json::json!({
            "error": msg
        })),
        TeacherError::DatabaseError(msg) => {
            log::error!("[Teacher] 数据库错误 | error={}", msg);
            internal_error("服务器内部错误")
        }
    }
}

/// 获取有效教师列表（公开API）
#[get("/teachers")]
async fn get_teachers(data: web::Data<AppState>) -> impl Responder {
    log::info!("[Teacher] 获取有效教师列表");

    match TeacherService::get_active_teachers(&data.pool).await {
        Ok(teachers) => {
            let response: Vec<serde_json::Value> = teachers
                .into_iter()
                .map(|t| {
                    serde_json::json!({
                        "sn": t.sn,
                        "name": t.name,
                        "department": t.department,
                    })
                })
                .collect();
            HttpResponse::Ok().json(response)
        }
        Err(e) => handle_teacher_error(e),
    }
}

/// 配置教师路由
pub fn config(cfg: &mut web::ServiceConfig) {
    cfg.service(get_teachers);
}
