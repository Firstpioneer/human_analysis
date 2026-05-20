# AI 招聘评估系统

可验证的 AI 招聘评估系统，集成人才画像、简历分析、AI 面试三大模块，通过 LLM 实现从岗位定义到面试评估的全流程智能化。

## 系统架构

```
system/
├── run.py                    # 启动入口
├── config.py                 # 统一配置（端口、数据目录）
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── migrate_data.py           # 数据迁移脚本
│
├── app/                      # FastAPI 后端
│   ├── main.py               # 应用工厂、路由注册、静态文件挂载
│   ├── routers/              # API 路由层
│   │   ├── portrait.py       # /api/portrait/*  画像模块
│   │   ├── resume.py         # /api/resume/*    简历模块
│   │   ├── interview.py      # /api/interview/* 面试模块
│   │   └── llm_config.py     # /api/llm/*       LLM 配置
│   ├── services/             # 业务逻辑层
│   │   ├── portrait/         # 画像生成（DeepSeek API）
│   │   ├── resume/           # 简历解析（DashScope / Qwen）
│   │   └── interview/        # 面试引擎（可配置 LLM）
│   ├── models/               # Pydantic 数据模型
│   ├── converters/           # 数据格式转换（画像→面试、简历→候选人）
│   ├── storage/              # 统一存储层（JSON 文件读写）
│   └── schemas/              # JSON Schema 定义
│
├── frontend/                 # 统一前端 SPA
│   ├── index.html            # 主页面（导航栏 + hash 路由）
│   ├── css/style.css         # 统一样式
│   └── js/
│       ├── api.js            # 统一 API 客户端
│       ├── router.js         # hash-based 前端路由
│       ├── portrait/         # 人才画像模块前端
│       ├── resume/           # 简历分析模块前端
│       └── interview/        # AI 面试模块前端
│
└── data/                     # 数据目录
    ├── conversations/        # 画像对话历史
    ├── profiles/             # 已确认的人才画像
    ├── candidates/           # 候选人档案
    ├── resumes/              # 简历解析结果
    ├── interviews/           # 面试记录
    │   ├── index.json        # 面试索引
    │   └── records/          # 单条面试记录（INT_*.json）
    └── schemas/              # JSON Schema
```

## 模块说明

### 人才画像（Portrait）

通过与 LLM 对话，逐步定义岗位的核心角色、信号维度、任职条件和排除画像，生成结构化的 `JobProfile`。

- LLM：DeepSeek（`https://api.deepseek.com`）
- API Key：通过前端设置，存储在浏览器 localStorage

### 简历分析（Resume）

上传 PDF/Word 简历，提取文本后调用 LLM 进行语义分析，分离"能力声明"与"客观经历"，识别信息盲区。

- LLM：阿里云 DashScope / Qwen（`https://dashscope.aliyuncs.com/compatible-mode/v1`）
- API Key：通过环境变量 `DASHSCOPE_API_KEY` 配置

### AI 面试（Interview）

根据人才画像自动生成面试方案，按方案逐题提问，支持追问、语音输入、计时控制，结束后生成评估报告。

- LLM：可配置（默认 DeepSeek，支持 OpenAI 兼容接口）
- 配置方式：前端页面设置，持久化到 `.env.json`

## 快速启动

### 1. 安装依赖

```bash
cd system
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

```bash
cp .env.example .env
# 编辑 .env，填入 DashScope API Key（简历模块需要）
```

也可直接设置环境变量：

```bash
# Windows PowerShell
$env:DASHSCOPE_API_KEY="your_key_here"

# Linux / macOS
export DASHSCOPE_API_KEY=your_key_here
```

### 3. 启动服务

```bash
python run.py
```

启动后访问 http://localhost:8000

### 4. 数据迁移（可选）

如果有 `ai-interview-engine` 的历史数据需要迁移：

```bash
python migrate_data.py
```

## 前端路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `#/portrait` | 人才画像 | 对话式岗位画像生成 |
| `#/resume` | 简历分析 | 上传简历、查看解析结果 |
| `#/interview` | AI 面试 | 选择画像和候选人，开始面试 |
| `#/interview/:id` | 面试房间 | 进行面试对话 |
| `#/records` | 面试记录 | 查看历史面试与评估 |

## API 端点

### 画像模块 `/api/portrait`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 与画像 Agent 对话 |
| POST | `/parse-jd` | 解析 JD 文本 |
| POST | `/generate-profile` | 生成结构化画像 |
| POST | `/save-profile` | 保存画像 |
| GET | `/profiles` | 画像列表 |
| GET | `/profiles/{id}` | 画像详情 |
| GET | `/conversations` | 对话历史列表 |
| GET | `/conversations/{id}` | 对话详情 |

### 简历模块 `/api/resume`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/parse` | 上传并解析简历 |
| GET | `/results` | 解析结果列表 |
| GET | `/results/{id}` | 解析结果详情 |

### 面试模块 `/api/interview`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/start` | 开始面试 |
| GET | `/next-question` | 获取下一个问题 |
| POST | `/answer` | 提交回答 |
| POST | `/ask-follow-up` | 追问 |
| POST | `/end` | 结束面试 |
| GET | `/status` | 面试状态 |
| GET | `/list` | 面试记录列表 |
| GET | `/detail/{id}` | 面试详情 |
| POST | `/restart/{id}` | 重新开始面试 |
| GET | `/profiles` | 画像列表（面试格式） |
| GET | `/candidates` | 候选人列表 |

### LLM 配置 `/api/llm`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/config` | 获取当前 LLM 配置 |
| POST | `/config` | 更新 LLM 配置 |
| POST | `/test` | 测试 LLM 连接 |

## LLM 配置说明

系统使用两套独立的 LLM 配置：

| 模块 | 默认模型 | API 地址 | 配置方式 |
|------|----------|----------|----------|
| 画像 | DeepSeek | `https://api.deepseek.com` | 前端 API Key 设置 |
| 简历 | Qwen-Max | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 环境变量 `DASHSCOPE_API_KEY` |
| 面试 | DeepSeek | `https://api.deepseek.com` | 前端页面设置，保存至 `.env.json` |

## 端到端工作流

```
定义岗位画像  ──→  上传候选人简历  ──→  启动 AI 面试  ──→  查看评估记录
 (portrait)       (resume)          (interview)        (records)
     │                │                   │                  │
     └── JobProfile ──┘                   │                  │
                     └── Candidate ───────┘                  │
                              └── Interview Record ──────────┘
```

1. 在「人才画像」页面通过对话生成岗位画像并保存
2. 在「简历分析」页面上传简历，系统自动解析并生成候选人档案
3. 在「AI 面试」页面选择画像和候选人，配置 LLM 后开始面试
4. 面试结束后在「面试记录」页面查看评估结果
