use chrono::NaiveDateTime;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// 评论实体
#[derive(Debug, sqlx::FromRow, Serialize)]
pub struct Comment {
    pub id: Uuid,
    pub resource_id: Uuid,
    pub user_id: Uuid,
    pub content: String,
    pub audit_status: String,
    pub created_at: NaiveDateTime,
    pub updated_at: NaiveDateTime,
}

/// 创建评论请求
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateCommentRequest {
    pub content: String,
}

/// 评论响应（包含用户信息）
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CommentResponse {
    pub id: Uuid,
    pub resource_id: Uuid,
    pub user_id: Uuid,
    pub user_name: String,
    pub user_avatar: Option<String>,
    pub content: String,
    pub created_at: String, // 使用 String 类型，在构造时格式化为 ISO 8601 格式
}

/// 评论列表查询
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CommentListQuery {
    pub page: Option<i64>,
    pub per_page: Option<i64>,
}

/// 评论列表响应
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CommentListResponse {
    pub comments: Vec<CommentResponse>,
    pub total: i64,
    pub page: i64,
    pub per_page: i64,
}

#[cfg(test)]
mod tests {
    use super::*;

    mod comment_list_query_tests {
        use super::*;

        #[test]
        fn test_comment_list_query_deserialization() {
            // 测试基本反序列化
            let json = r#"{"page": 1, "perPage": 20}"#;
            let query: CommentListQuery = serde_json::from_str(json).unwrap();
            assert_eq!(query.page, Some(1));
            assert_eq!(query.per_page, Some(20));
        }

        #[test]
        fn test_comment_list_query_default() {
            // 测试默认值
            let json = r#"{}"#;
            let query: CommentListQuery = serde_json::from_str(json).unwrap();
            assert_eq!(query.page, None);
            assert_eq!(query.per_page, None);
        }

        #[test]
        fn test_comment_list_query_partial() {
            // 测试部分字段
            let json = r#"{"page": 5}"#;
            let query: CommentListQuery = serde_json::from_str(json).unwrap();
            assert_eq!(query.page, Some(5));
            assert_eq!(query.per_page, None);
        }
    }

    mod create_comment_request_tests {
        use super::*;

        #[test]
        fn test_create_comment_request_deserialization() {
            let json = r#"{"content": "This is a test comment"}"#;
            let req: CreateCommentRequest = serde_json::from_str(json).unwrap();
            assert_eq!(req.content, "This is a test comment");
        }

        #[test]
        fn test_create_comment_request_empty_content() {
            let json = r#"{"content": ""}"#;
            let req: CreateCommentRequest = serde_json::from_str(json).unwrap();
            assert_eq!(req.content, "");
        }

        #[test]
        fn test_create_comment_request_long_content() {
            let content = "a".repeat(1000);
            let json = format!(r#"{{"content": "{}"}}"#, content);
            let req: CreateCommentRequest = serde_json::from_str(&json).unwrap();
            assert_eq!(req.content.len(), 1000);
        }
    }

    mod comment_response_tests {
        use super::*;

        #[test]
        fn test_comment_response_serialization() {
            let resource_id = Uuid::new_v4();
            let user_id = Uuid::new_v4();
            let comment_id = Uuid::new_v4();

            let response = CommentResponse {
                id: comment_id,
                resource_id,
                user_id,
                user_name: "test_user".to_string(),
                user_avatar: Some("http://example.com/avatar.png".to_string()),
                content: "Test content".to_string(),
                created_at: "2024-01-01T00:00:00Z".to_string(),
            };

            let json = serde_json::to_string(&response).unwrap();
            assert!(json.contains("resourceId"));
            assert!(json.contains("userId"));
            assert!(json.contains("userName"));
            assert!(json.contains("userAvatar"));
            assert!(json.contains("createdAt"));
            assert!(json.contains("Test content"));
        }

        #[test]
        fn test_comment_response_without_avatar() {
            let resource_id = Uuid::new_v4();
            let user_id = Uuid::new_v4();
            let comment_id = Uuid::new_v4();

            let response = CommentResponse {
                id: comment_id,
                resource_id,
                user_id,
                user_name: "test_user".to_string(),
                user_avatar: None,
                content: "Test content".to_string(),
                created_at: "2024-01-01T00:00:00Z".to_string(),
            };

            let json = serde_json::to_string(&response).unwrap();
            assert!(json.contains("null"));
        }
    }

    mod comment_list_response_tests {
        use super::*;

        #[test]
        fn test_comment_list_response_serialization() {
            let resource_id = Uuid::new_v4();
            let user_id = Uuid::new_v4();

            let response = CommentListResponse {
                comments: vec![CommentResponse {
                    id: Uuid::new_v4(),
                    resource_id,
                    user_id,
                    user_name: "test_user".to_string(),
                    user_avatar: None,
                    content: "Test".to_string(),
                    created_at: "2024-01-01T00:00:00Z".to_string(),
                }],
                total: 1,
                page: 1,
                per_page: 20,
            };

            let json = serde_json::to_string(&response).unwrap();
            assert!(json.contains("comments"));
            assert!(json.contains("total"));
            assert!(json.contains("page"));
            assert!(json.contains("perPage"));
        }

        #[test]
        fn test_comment_list_response_empty() {
            let response = CommentListResponse {
                comments: vec![],
                total: 0,
                page: 1,
                per_page: 20,
            };

            let json = serde_json::to_string(&response).unwrap();
            assert!(json.contains("\"comments\":[]"));
            assert!(json.contains("\"total\":0"));
        }
    }
}
