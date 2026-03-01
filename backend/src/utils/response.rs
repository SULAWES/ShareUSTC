// 统一响应处理工具

use actix_web::HttpResponse;

/// 构建错误响应
pub fn error_response(status: u16, message: &str) -> HttpResponse {
    let error = match status {
        400 => "BadRequest",
        401 => "Unauthorized",
        403 => "Forbidden",
        404 => "NotFound",
        409 => "Conflict",
        422 => "UnprocessableEntity",
        500 => "InternalServerError",
        502 => "BadGateway",
        503 => "ServiceUnavailable",
        _ => "UnknownError",
    };

    HttpResponse::build(
        actix_web::http::StatusCode::from_u16(status)
            .unwrap_or(actix_web::http::StatusCode::INTERNAL_SERVER_ERROR),
    )
    .json(serde_json::json!({
        "error": error,
        "message": message
    }))
}

/// 快速构建 400 Bad Request 错误
pub fn bad_request(message: &str) -> HttpResponse {
    error_response(400, message)
}

/// 快速构建 401 Unauthorized 错误
pub fn unauthorized(message: &str) -> HttpResponse {
    error_response(401, message)
}

/// 快速构建 403 Forbidden 错误
pub fn forbidden(message: &str) -> HttpResponse {
    error_response(403, message)
}

/// 快速构建 404 Not Found 错误
pub fn not_found(message: &str) -> HttpResponse {
    error_response(404, message)
}

/// 快速构建 409 Conflict 错误
pub fn conflict(message: &str) -> HttpResponse {
    error_response(409, message)
}

/// 快速构建 500 Internal Server Error 错误
pub fn internal_error(message: &str) -> HttpResponse {
    error_response(500, message)
}

/// 构建创建成功响应（201 Created）
pub fn created<T: serde::Serialize>(data: T) -> HttpResponse {
    HttpResponse::Created().json(data)
}

/// 构建无内容响应（204 No Content）
pub fn no_content() -> HttpResponse {
    HttpResponse::NoContent().finish()
}

#[cfg(test)]
mod tests {
    use super::*;

    mod error_response_tests {
        use super::*;

        #[test]
        fn test_error_response_400() {
            let response = error_response(400, "Bad request message");
            assert_eq!(response.status(), 400);
        }

        #[test]
        fn test_error_response_401() {
            let response = error_response(401, "Unauthorized");
            assert_eq!(response.status(), 401);
        }

        #[test]
        fn test_error_response_403() {
            let response = error_response(403, "Forbidden");
            assert_eq!(response.status(), 403);
        }

        #[test]
        fn test_error_response_404() {
            let response = error_response(404, "Not found");
            assert_eq!(response.status(), 404);
        }

        #[test]
        fn test_error_response_409() {
            let response = error_response(409, "Conflict");
            assert_eq!(response.status(), 409);
        }

        #[test]
        fn test_error_response_500() {
            let response = error_response(500, "Internal server error");
            assert_eq!(response.status(), 500);
        }

        #[test]
        fn test_error_response_unknown_status() {
            let response = error_response(418, "I'm a teapot");
            assert_eq!(response.status(), 418);
        }
    }

    mod helper_functions_tests {
        use super::*;

        #[test]
        fn test_bad_request() {
            let response = bad_request("Invalid input");
            assert_eq!(response.status(), 400);
        }

        #[test]
        fn test_unauthorized() {
            let response = unauthorized("Please login");
            assert_eq!(response.status(), 401);
        }

        #[test]
        fn test_forbidden() {
            let response = forbidden("Access denied");
            assert_eq!(response.status(), 403);
        }

        #[test]
        fn test_not_found() {
            let response = not_found("Resource not found");
            assert_eq!(response.status(), 404);
        }

        #[test]
        fn test_conflict() {
            let response = conflict("Resource already exists");
            assert_eq!(response.status(), 409);
        }

        #[test]
        fn test_internal_error() {
            let response = internal_error("Something went wrong");
            assert_eq!(response.status(), 500);
        }

        #[test]
        fn test_created() {
            #[derive(serde::Serialize)]
            struct TestData {
                id: i32,
                name: String,
            }

            let data = TestData {
                id: 1,
                name: "Test".to_string(),
            };
            let response = created(data);
            assert_eq!(response.status(), 201);
        }

        #[test]
        fn test_no_content() {
            let response = no_content();
            assert_eq!(response.status(), 204);
        }
    }
}
