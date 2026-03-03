use actix_web::{get, web, HttpResponse, Responder};

use crate::db::AppState;
use crate::services::{CourseError, CourseService};
use crate::utils::{bad_request, internal_error, not_found};

/// 将 CourseError 转换为 HttpResponse
fn handle_course_error(err: CourseError) -> HttpResponse {
    match err {
        CourseError::NotFound(msg) => not_found(&msg),
        CourseError::ValidationError(msg) => bad_request(&msg),
        CourseError::DatabaseError(msg) => {
            log::error!("[Course] 数据库错误 | error={}", msg);
            internal_error("服务器内部错误")
        }
    }
}

/// 获取有效课程列表（公开API）
#[get("/courses")]
async fn get_courses(data: web::Data<AppState>) -> impl Responder {
    log::info!("[Course] 获取有效课程列表");

    match CourseService::get_active_courses(&data.pool).await {
        Ok(courses) => {
            let response: Vec<serde_json::Value> = courses
                .into_iter()
                .map(|c| {
                    serde_json::json!({
                        "sn": c.sn,
                        "name": c.name,
                        "semester": c.semester,
                        "credits": c.credits,
                    })
                })
                .collect();
            HttpResponse::Ok().json(response)
        }
        Err(e) => handle_course_error(e),
    }
}

/// 配置课程路由
pub fn config(cfg: &mut web::ServiceConfig) {
    cfg.service(get_courses);
}
