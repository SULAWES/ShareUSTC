use serde::Serialize;

/// 点赞状态响应
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct LikeStatusResponse {
    pub is_liked: bool,
    pub like_count: i64,
}

/// 点赞操作响应
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct LikeToggleResponse {
    pub is_liked: bool,
    pub like_count: i64,
    pub message: String,
}
