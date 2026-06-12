<<<<<<< HEAD
# BBWorkbench
=======
# AI 招聘评估系统

可验证的 AI 招聘评估系统，集成人才画像、简历分析、AI 面试三大模块，通过 LLM 实现从岗位定义到面试评估的全流程智能化。AI 面试采用语音优先交互：AI 语音提问，候选人语音回答，基于画像信号维度和简历证据动态生成问题与追问。

## 系统架构

```
system/
├── run.py                    # 启动入口
├── config.py                 # 统一配置（端口、数据目录）
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
│
├── app/                      # FastAPI 后端
│   ├── main.py               # 应用工厂、路由注册、静态文件挂载
│   ├── routers/              # API 路由层
│   │   ├── portrait.py       # /api/portrait/*  画像模块（保存时自动同步面试画像）
│   │   ├── resume.py         # /api/resume/*    简历模块（解析时自动同步候选人）
│   │   ├── interview.py      # /api/interview/* 面试模块
│   │   └── llm_config.py     # /api/llm/*       LLM 配置
│   ├── services/             # 业务逻辑层
│   │   ├── portrait/         # 画像生成（DeepSeek API）
│   │   ├── resume/           # 简历解析（DashScope / Qwen）
│   │   └── interview/        # 面试引擎（可配置 LLM）
│   ├── models/               # Pydantic 数据模型
│   ├── converters/           # 数据格式转换
│   │   ├── profile_converter.py    # 画像 → 面试画像格式
│   │   └── candidate_converter.py  # 简历 → 候选人格式
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
│           ├── setup.js      # 面试设置页（选择画像 + 简历来源）
│           ├── room.js       # 面试房间（语音优先状态机）
│           └── records.js    # 面试记录
│
└── data/                     # 数据目录
    ├── conversations/        # 画像对话历史
    ├── profiles/             # 已确认的人才画像
    ├── candidates/           # 候选人档案
    ├── resumes/              # 简历解析结果
    ├── interviews/           # 面试记录
    │   ├── index.json        # 面试索引
    │   ├── records/          # 单条面试记录（INT_*.json）
    │   ├── profiles.json     # 面试画像库（画像模块自动同步）
    │   └── candidates.json   # 面试候选人库（简历模块自动同步）
    └── schemas/              # JSON Schema
```

## 模块说明

### 人才画像（Portrait）

通过与 LLM 对话，逐步定义岗位的核心角色、信号维度、任职条件和排除画像，生成结构化的 `JobProfile`。

- LLM：DeepSeek（`https://api.deepseek.com`）
- API Key：通过前端设置，存储在浏览器 localStorage
- 保存画像后自动转换并同步到面试画像库，返回 `interview_profile_id` 供面试启动使用

### 简历分析（Resume）

上传 PDF/Word 简历，提取文本后调用 LLM 进行语义分析，分离"能力声明"与"客观经历"，识别信息盲区。

- 文本抽取：`pdfplumber`、`python-docx`、`mammoth`，图片型 PDF/图片简历可通过 `PyMuPDF + PaddleOCR` 回退 OCR
- LLM：默认阿里云 DashScope / Qwen（`https://dashscope.aliyuncs.com/compatible-mode/v1`），也支持 OpenAI SDK 兼容网关
- API Key：通过环境变量 `RESUME_LLM_API_KEY` 配置，兼容旧变量 `DASHSCOPE_API_KEY`
- 外部足迹：自动识别 GitHub、仓库链接和技术博客 URL，抓取语言、仓库活跃度、博客标题/标签
- 解析成功后自动转换并保存为面试候选人，返回 `candidate_id` 供面试启动使用

### AI 面试（Interview）

根据人才画像和简历分析结果自动生成面试方案，结合画像信号维度与候选人简历证据动态设计问题，采用语音优先交互模式。

- LLM：可配置（默认 DeepSeek，支持 OpenAI 兼容接口）
- 配置方式：前端页面设置，持久化到 `.env.json`
- 面试设置页要求选择已保存的人才画像输出和简历分析结果，不再支持手动填写岗位/技能预设
- 语音交互：浏览器 TTS 播报问题，ASR 录制候选人口述回答
- 追问策略：每个问题最多追问 2 次，由 LLM 根据回答质量决定

## 快速启动

### 1. 安装依赖

```bash
cd system
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

```bash
cp .env.example .env
# 编辑 .env，填入 LLM API Key（简历、画像和面试模块需要）
```

也可直接设置环境变量：

```bash
# Windows PowerShell（OpenAI SDK 兼容网关）
$env:RESUME_LLM_API_KEY="your_key_here"
$env:RESUME_LLM_BASE_URL="https://ai-gateway.ailab.jiuan.com/v1"
$env:RESUME_LLM_MODEL="gpt-4o-mini"

# Linux / macOS（OpenAI SDK 兼容网关）
export RESUME_LLM_API_KEY=your_key_here
export RESUME_LLM_BASE_URL=https://ai-gateway.ailab.jiuan.com/v1
export RESUME_LLM_MODEL=gpt-4o-mini
```

### 3. 启动服务

```bash
python run.py
```

启动后访问 http://localhost:8000

## 前端路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `#/portrait` | 人才画像 | 对话式岗位画像生成 |
| `#/resume` | 简历分析 | 上传简历、查看解析结果 |
| `#/interview` | AI 面试 | 选择画像输出和简历分析结果后开始面试 |
| `#/interview/:id` | 面试房间 | 语音优先面试交互（AI 语音提问 → 候选人语音回答） |
| `#/records` | 面试记录 | 查看历史面试与评估 |

## API 端点

### 画像模块 `/api/portrait`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 与画像 Agent 对话 |
| POST | `/parse-jd` | 解析 JD 文本 |
| POST | `/generate-profile` | 生成结构化画像 |
| POST | `/save-profile` | 保存画像（同步写入面试画像库，返回 `interview_profile_id`） |
| GET | `/profiles` | 画像列表 |
| GET | `/profiles/{id}` | 画像详情 |
| GET | `/conversations` | 对话历史列表 |
| GET | `/conversations/{id}` | 对话详情 |

### 简历模块 `/api/resume`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/parse` | 上传并解析简历（自动保存为面试候选人，返回 `candidate_id`） |
| GET | `/results` | 解析结果列表 |
| GET | `/results/{id}` | 解析结果详情 |

### 面试模块 `/api/interview`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/start` | 开始面试（必须提供 `profile_id` + `candidate_id`） |
| POST | `/next-question` | 获取下一个问题 |
| POST | `/answer` | 提交回答（支持追问元数据） |
| POST | `/ask-follow-up` | 追问 |
| POST | `/end` | 结束面试 |
| POST | `/status` | 面试状态 |
| GET | `/list` | 面试记录列表 |
| GET | `/detail/{id}` | 面试详情 |
| POST | `/restart/{id}` | 重新开始面试 |
| GET | `/profiles` | 面试画像列表 |
| GET | `/candidates` | 面试候选人列表 |

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
| 画像 | DeepSeek / 可切网关模型 | `PORTRAIT_LLM_BASE_URL`，默认 `https://api.deepseek.com` | 前端 API Key + 环境变量 Base URL/Model |
| 简历 | Qwen-Max / 可切网关模型 | `RESUME_LLM_BASE_URL`，默认 `https://dashscope.aliyuncs.com/compatible-mode/v1` | 环境变量 `RESUME_LLM_API_KEY` |
| 面试 | DeepSeek / 可切网关模型 | 前端可选 `https://ai-gateway.ailab.jiuan.com/v1` | 前端页面设置，保存至 `.env.json` |

### 九安 AI Gateway 配置示例

OpenAI SDK 兼容调用：

```python
from openai import OpenAI

client = OpenAI(
    api_key="your_api_key_here",
    base_url="https://ai-gateway.ailab.jiuan.com/v1",
)
```

Anthropic SDK 兼容调用：

```python
from anthropic import Anthropic

client = Anthropic(
    api_key="your_api_key_here",
    base_url="https://ai-gateway.ailab.jiuan.com",
)
```

本项目后端的简历和面试模块当前通过 OpenAI SDK 兼容接口调用。要使用九安网关，请优先设置：

```bash
RESUME_LLM_API_KEY=your_api_key_here
RESUME_LLM_BASE_URL=https://ai-gateway.ailab.jiuan.com/v1
RESUME_LLM_MODEL=gpt-4o-mini

LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://ai-gateway.ailab.jiuan.com/v1
LLM_MODEL=gpt-4o-mini
```

画像模块如果也走同一网关：

```bash
PORTRAIT_LLM_BASE_URL=https://ai-gateway.ailab.jiuan.com/v1
PORTRAIT_LLM_MODEL=gpt-4o-mini
```

## 数据流转

```
人才画像页面                简历分析页面
     │                          │
     ▼                          ▼
 /api/portrait/save-profile   /api/resume/parse
     │                          │
     ├─ 保存原始画像            ├─ 保存简历解析结果
     └─ portrait_to_interview_profile()
           │                    └─ resume_to_interview_candidate()
           ▼                          ▼
   data/interviews/profiles.json   data/interviews/candidates.json
           │                          │
           └──────────┬───────────────┘
                      ▼
              AI 面试设置页
           选择画像 + 选择候选人
                      │
                      ▼
           /api/interview/start
           (profile_id + candidate_id)
                      │
                      ▼
              InterviewEngine
         ┌────────────┴────────────┐
         ▼                         ▼
   QuestionGenerator         FollowUpStrategy
   (画像信号维度 +             (回答质量判断
    简历盲点/经历)              最多追问2次)
         │                         │
         ▼                         ▼
      面试房间 (语音交互)
      AI TTS 播报问题
      候选人 ASR 回答
                      │
                      ▼
              /api/interview/end
                      │
                      ▼
              评估报告生成
```

## 面试房间语音交互

面试房间采用语音优先的状态机模式：

| 状态 | 说明 | 候选人操作 |
|------|------|-----------|
| `preparing` | 加载面试方案，检测浏览器语音能力 | 等待 |
| `ai_speaking` | AI 语音播报问题（浏览器 TTS） | 听问题，不可录音 |
| `candidate_answering` | 候选人语音回答（浏览器 ASR） | 按住按钮或点击回答，转写内容不实时显示 |
| `ai_thinking` | 后端判断是否追问或下一题 | 等待 |
| `completed` | 面试结束 | 查看结果 |

- AI 首次提问前需要用户点击"开始语音面试"按钮以解除浏览器语音播放限制
- 如果浏览器不支持 TTS/ASR，页面自动降级为文字展示 + 手动输入
- 追问内容由 LLM 根据候选人回答质量动态生成，每个问题最多追问 2 次
>>>>>>> origin/main
