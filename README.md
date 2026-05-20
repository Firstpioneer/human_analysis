# AI 招聘画像系统 — 需求 Agent + 画像构建

方向一：通过与 AI Agent 的多轮对话，将模糊的招聘需求转化为结构化人才画像。

## 快速启动

### 1. 安装依赖

```bash
cd code/backend
pip install -r requirements.txt
```

### 2. 启动后端

```bash
cd code/backend
uvicorn main:app --reload --port 8000
```

看到以下输出说明启动成功：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. 打开前端

浏览器打开 `code/frontend/index.html`，首次打开会提示输入 DeepSeek API Key。

> 也可以用 VS Code Live Server 打开，或直接双击 index.html。

## 使用流程

1. **输入 API Key** — 弹框中填入 DeepSeek API Key（仅保存在浏览器本地）
2. **粘贴 JD** — 将岗位描述粘贴到对话框，发送
3. **与 Agent 对话** — Agent 会解析 JD 并追问细节（团队背景、选人标准、排除条件等）
4. **生成画像** — 输入"生成画像"，左侧预览结构化人才画像
5. **编辑/导出** — 支持编辑 JSON、导出文件、保存到服务器
6. **历史管理** — 点击"历史"查看所有对话记录，支持加载和删除

## 目录结构

```
code/
├── backend/
│   ├── main.py               # FastAPI 入口 + 路由
│   ├── agent.py              # Agent 核心（DeepSeek API 调用 + 对话管理）
│   ├── prompts.py            # 系统提示词（JD解析、追问策略、画像生成）
│   ├── profile_generator.py  # 画像验证 + 保存 + 加载
│   ├── conversation_store.py # 对话历史存储
│   ├── models.py             # Pydantic 数据模型
│   └── requirements.txt
├── frontend/
│   ├── index.html            # 主页面
│   ├── css/style.css         # 深蓝科技主题样式
│   └── js/
│       ├── api.js            # API 调用封装
│       ├── chat.js           # 聊天模块
│       ├── profile.js        # 画像预览/编辑
│       └── app.js            # 主应用逻辑
└── data/
    ├── conversations/        # 对话历史（自动保存）
    └── profiles/             # 已确认的画像
```

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | HTML + CSS + JS |
| 后端 | Python FastAPI |
| LLM | DeepSeek API (deepseek-chat) |
| 存储 | JSON 文件 |

## API 接口

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/chat` | POST | 发送消息，返回 Agent 回复 |
| `/api/conversations` | GET | 列出所有对话历史 |
| `/api/conversations/{id}` | GET | 加载指定对话 |
| `/api/conversations/{id}` | DELETE | 删除指定对话 |
| `/api/profiles` | GET | 列出已保存画像 |
| `/api/profiles/{id}` | GET | 加载指定画像 |
| `/api/save-profile` | POST | 正式保存画像 |
| `/api/health` | GET | 健康检查 |
