# ShareUSTC 部署指南

版本：2.0  
更新日期：2026-02-12  
适用范围：本地开发环境（Ubuntu）与基础生产部署准备

## 1. 环境要求

- Node.js >= 18（建议 20+）
- Rust stable（2021 edition）
- PostgreSQL >= 14
- 阿里云 OSS + RAM（用于 STS 直传与签名下载）

## 2. 安装基础依赖

### 2.1 Node.js / npm

```bash
sudo apt update
sudo apt install -y npm
```

如需更高版本 Node.js，请使用 nvm 或 NodeSource。

### 2.2 Rust

```bash
sudo apt install -y rustup pkg-config
rustup install stable
rustup default stable
```

### 2.3 PostgreSQL

```bash
sudo apt install -y postgresql
```

## 3. 初始化数据库

进入 PostgreSQL 管理终端：

```bash
sudo -u postgres psql
```

创建数据库用户与库：

```sql
CREATE USER shareustc_app WITH PASSWORD 'ShareUSTC_default_pwd';

CREATE DATABASE shareustc
    WITH
    OWNER = shareustc_app
    ENCODING = 'UTF8'
    LC_COLLATE = 'C.UTF-8'
    LC_CTYPE = 'C.UTF-8'
    TEMPLATE = template0;

GRANT ALL PRIVILEGES ON DATABASE shareustc TO shareustc_app;
\q
```

在项目根目录执行建表脚本：

```bash
./scripts/db_init_tables.sh
```

## 4. 阿里云 OSS 准备

当前上传链路为 STS 直传 OSS，必须完成以下配置：

1. 创建私有 Bucket（建议开启阻止公共访问）。
2. 创建可 AssumeRole 的 RAM 角色。
3. 为后端长期 AK 配置最小权限：
   - `sts:AssumeRole`
   - OSS 对象签名/删除所需权限
4. 为 STS 角色配置上传权限，仅允许：
   - `resources/*`
   - `images/*`

详细策略参考：`dev_doc/oss_moderation_plan.md`

## 5. 配置后端环境变量

```bash
cd backend
cp .env.example .env
```

至少确认以下变量：

- `DATABASE_URL`
- `JWT_SECRET`
- `SERVER_HOST`
- `SERVER_PORT`
- `ALIYUN_ACCESS_KEY_ID`
- `ALIYUN_ACCESS_KEY_SECRET`
- `OSS_BUCKET`
- `OSS_REGION`
- `OSS_ENDPOINT`
- `OSS_PUBLIC_URL`
- `STS_ROLE_ARN`
- `STS_SESSION_DURATION`

注意：`IMAGE_UPLOAD_PATH` / `RESOURCE_UPLOAD_PATH` 为本地历史文件兼容路径（fallback）。

## 6. 启动服务

### 6.1 启动后端

```bash
cd backend
cargo run
```

默认地址：`http://127.0.0.1:8080`

### 6.2 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：`http://localhost:5173`

## 7. 构建检查（推荐）

```bash
cd frontend && npm run build
cd ../backend && cargo check
```

若后端在受限环境中失败，请在可访问数据库且具备 SQLx 校验条件的本机执行。

## 8. 生产环境注意事项

1. 修改 `JWT_SECRET` 与数据库密码为强随机值。
2. 后端仅保留必要 CORS 域名。
3. 使用 Nginx 反向代理并启用 HTTPS。
4. OSS Bucket 保持私有，图片通过 `/images/{id}` 由后端签名跳转访问。
5. 建议将日志级别设置为 `info`，并接入集中化日志系统。
