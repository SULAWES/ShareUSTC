use actix_cors::Cors;
use actix_web::{get, web, App, HttpResponse, HttpServer, Responder};
use serde::Serialize;
use std::sync::atomic::{AtomicUsize, Ordering};

#[derive(Serialize)]
struct HelloResponse {
    message: String,
}

// 共享状态结构体
struct AppState {
    counter: AtomicUsize,
}

#[get("/api/hello")]
async fn hello(data: web::Data<AppState>) -> impl Responder {
    let count = data.counter.fetch_add(1, Ordering::SeqCst);
    HttpResponse::Ok().json(HelloResponse {
        message: format!("Hello from Rust backend! Request count: {}", count + 1),
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    println!("Starting server at http://localhost:8080");

    // 创建应用状态
    let app_state = web::Data::new(AppState {
        counter: AtomicUsize::new(0),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone()) // 将状态传递给每个应用程序实例
            .wrap(
                Cors::default()
                    .allowed_origin("http://localhost:5173")
                    .allowed_methods(vec!["GET", "POST"])
                    .allowed_headers(vec!["Content-Type"])
            )
            .service(hello)
    })
        .bind("127.0.0.1:8080")?
        .run()
        .await
}