# Feishu Bitable Configuration

## Environment Variables

```bash
# Required
export FEISHU_BITABLE_APP_TOKEN="your_app_token"
export FEISHU_BITABLE_TABLE_ID="your_table_id"

# User access token (auto-managed by OpenClaw token store)
# Location: ~/.openclaw/tokens/feishu/default/user_access_token
export FEISHU_USER_ACCESS_TOKEN="your_user_token"  # Optional, auto-detected
```

## Bitable Field Structure

| Field Name | Type | Description |
|------------|------|-------------|
| 标题 | Text | Content title (searchable) |
| 来源 | Text | Author/platform (filterable) |
| 分类 | Single Select | Category (filterable) |
| 原文链接 | URL | Original source link |
| 摘要内容 | Text | AI-generated summary (searchable) |
| 记录时间 | Created Time | Auto-recorded |
| 原文文件 | URL | Feishu Drive .md file link |

## Category Options

- 🔧 工具推荐
- 📖 技术教程
- 🛠️ 实战案例
- 💡 产品想法

## API Endpoints

### Create Record

```
POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records
```

### Update Record

```
PUT /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}
```

## Authentication

The skill reads user access token from:

1. Environment variable `FEISHU_USER_ACCESS_TOKEN`
2. OpenClaw token store: `~/.openclaw/tokens/feishu/default/user_access_token`
3. Command-line argument `--token`

## URLs

- Bitable: `https://my.feishu.cn/base/{app_token}?table={table_id}`
- File upload: Use `feishu_drive_file upload` tool
