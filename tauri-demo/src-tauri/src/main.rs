#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// 自定义 IPC 命令
#[tauri::command]
async fn greet(name: &str) -> String {
    format!("你好, {}! 这是来自 Rust 后端的响应", name)
}

fn main() {
    tauri::Builder::default()
        // 注册自定义命令
        .invoke_handler(tauri::generate_handler![greet])
        // 构建应用
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用失败");
}