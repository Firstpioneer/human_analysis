# AI 面试引擎

> 基于大语言模型的智能面试系统，自动生成面试方案、实时追问、语音交互、面试评估一站式完成。

---

## 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [配置大语言模型](#配置大语言模型)
- [项目结构](#项目结构)
- [功能演示](#功能演示)
- [API 文档](#api-文档)
- [数据格式](#数据格式)
- [常见问题](#常见问题)

---

## 功能特性

### 方向三：AI 面试引擎

| 功能 | 说明 |
|------|------|
| 🧠 **智能问题生成** | 大语言模型根据岗位画像 + 候选人简历动态生成面试问题，零预设模板 |
| 💬 **实时追问** | LLM 理解候选人回答上下文，自动判断是否需要追问并生成追问内容 |
| ⏱ **时间控制** | 自动分配各环节时长，超时预警，节奏建议（加快/深入/收尾） |
| 🎤 **语音交互** | 前端 Web Speech API，支持语音输入（ASR）和语音播报（TTS） |
| 📋 **面试方案** | 自动编排技术考察、项目经验、软技能与文化契合等环节 |
| 📝 **面试评估** | LLM 对整场面试进行专业评估（多维度评分 + 优缺点 + 推荐结论） |
| 🔄 **重新开始** | 已完成的面试可一键重新面试，LLM 生成全新问题 |
| 💾 **记录持久化** | 所有面试数据保存为 JSON，可随时回放查看 |

### 对接方向一、方向二

系统可接收来自"方向一（人才画像）"和"方向二（候选人档案）"的数据作为输入，打通完整招聘链路。

---

## 快速开始

### 环境要求

- Python ≥ 3.8
- 浏览器（推荐 Chrome，支持语音识别）

### 1️⃣ 安装依赖

```bash
cd ai-interview-engine
pip install flask openai<1.60
```

### 2️⃣ 启动服务

```bash
# Windows (使用虚拟环境)
d:/实习/.venv/Scripts/python.exe app.py

# 或直接
python app.py
```

启动后访问：**http://127.0.0.1:5000**

### 3️⃣ 配置 LLM

在页面底部 **「大语言模型配置」** 面板中填入：

1. **提供商** — 选择 DeepSeek / OpenAI / Moonshot 等
2. **API Key** — 输入你的 API 密钥
3. **API 地址** — 自动填充对应提供商地址
4. **模型名称** — 如 `deepseek-chat` / `gpt-4o-mini`
5. 点击 **「测试连接」** 验证 → 点击 **「保存配置」**

> 也可通过环境变量配置（优先级高于页面配置）：
>
> ```powershell
> $env:LLM_API_KEY="sk-xxx"
> $env:LLM_BASE_URL="https://api.deepseek.com/v1"
> $env:LLM_MODEL="deepseek-chat"
> python app.py
> ```

### 4️⃣ 开始面试

1. 填写岗位名称和技能要求（或使用默认值）
2. 点击 **「🎙️ 开始 AI 面试」**
3. 进入面试房间，AI 自动提问
4. 输入回答或点击 🎤 语音输入
5. 面试结束自动生成评估报告

---

## 项目结构

```
ai-interview-engine/
├── app.py                          # Flask Web 主应用 + 路由
├── demo.py                         # 命令行功能演示
├── requirements.txt                # Python 依赖
├── .env.json                       # LLM 配置（页面保存生成）
│
├── modules/
│   ├── __init__.py
│   ├── llm_service.py              # 大语言模型服务抽象层
│   ├── question_generator.py       # 面试问题方案生成
│   ├── follow_up_strategy.py       # 追问策略 + 时间控制
│   ├── interview_engine.py         # 面试引擎核心协调器
│   ├── speech_service.py           # 语音服务抽象层
│   └── storage.py                  # 面试记录持久化
│
├── templates/
│   ├── index.html                  # 首页（配置 + 启动面试）
│   ├── interview.html              # 面试房间（对话 + 计时 + 语音）
│   └── records.html                # 面试记录列表
│
├── static/
│   └── css/
│       └── style.css               # 全局样式
│
└── data/
    ├── schemas/
    │   ├── profile_schema.json     # 人才画像 Schema
    │   ├── candidate_schema.json   # 候选人档案 Schema
    │   └── interview_schema.json   # 面试记录 Schema
    ├── interviews.json             # 面试索引
    └── records/                    # 每场面试的完整记录
        └── INT_*.json
```

### 核心模块说明

| 模块 | 职责 |
|------|------|
| `llm_service.py` | OpenAI 兼容接口封装，支持 `chat` / `chat_json`，含面试专用方法 |
| `question_generator.py` | 将完整画像+简历发给 LLM，LLM 自主生成全部环节和问题 |
| `follow_up_strategy.py` | LLM 理解候选人回答，判断是否需要追问并生成追问内容 |
| `interview_engine.py` | 协调全流程：问题生成 → 追问 → 时间控制 → 记录存储 |
| `speech_service.py` | 后端语音服务抽象，前端 Web Speech API 实现实时交互 |
| `storage.py` | JSON 文件持久化，CRUD 接口 |

---

## 功能演示

命令行演示（无需启动 Web）：

```bash
python demo.py
```

包含 4 个演示模块：

```
╔══════════════════════════════════════════════╗
║        AI 面试引擎 v1.0 - 功能演示           ║
╚══════════════════════════════════════════════╝

演示 1: 面试问题方案自动生成    ← LLM 动态生成
演示 2: 追问策略                ← LLM 理解上下文追问
演示 3: 时间控制                ← 各环节进度管理
演示 4: 完整 AI 面试流程        ← 全流程模拟
```

---

## API 文档

### 面试流程

| 方法 | 路由 | 说明 |
|------|------|------|
| `POST` | `/api/interview/start` | 开始新面试（需 `profile` 画像） |
| `POST` | `/api/interview/next-question` | 获取下一问题（参数 `elapsed_minutes`） |
| `POST` | `/api/interview/answer` | 提交回答（参数 `question_id` + `answer`） |
| `POST` | `/api/interview/ask-follow-up` | AI 发出追问 |
| `POST` | `/api/interview/end` | 结束面试，生成评估 |
| `POST` | `/api/interview/status` | 获取面试时间状态 |
| `POST` | `/api/interview/<id>/restart` | 基于已有记录重新开始 |

### 记录管理

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/interviews` | 获取面试列表 |
| `GET` | `/api/interview/<id>` | 获取单场面试详情 |
| `DELETE` | `/api/interview/<id>` | 删除面试记录 |

### LLM 配置

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/llm/config` | 获取当前 LLM 配置状态 |
| `POST` | `/api/llm/config` | 更新 LLM 配置 |
| `POST` | `/api/llm/test` | 测试 LLM 连接 |
| `POST` | `/api/llm/toggle` | 启用/禁用 LLM 模式 |

---

## 数据格式

系统定义了 3 个 JSON Schema，位于 `data/schemas/`：

| Schema | 说明 | 来源 |
|--------|------|------|
| `profile_schema.json` | 人才画像 | 方向一输出 |
| `candidate_schema.json` | 候选人档案 | 方向二输出 |
| `interview_schema.json` | 面试全过程记录 | 本系统输出 |

### 面试记录结构

```json
{
  "interview_id": "INT_3E0BF8BB",
  "candidate": {
    "name": "张三",
    "profile_ref": "高级后端开发工程师"
  },
  "start_time": "2026-05-18T00:38:08",
  "end_time": null,
  "status": "进行中",
  "plan": {
    "total_duration_minutes": 45,
    "sections": [
      {
        "section_name": "技术基础考察",
        "duration_minutes": 20,
        "focus_area": "核心技能评估",
        "questions": [...]
      }
    ]
  },
  "dialogues": [
    {"speaker": "AI", "text": "..."},
    {"speaker": "候选人", "text": "..."}
  ],
  "evaluation": {
    "overall_score": 85,
    "dimension_scores": {"技术能力": 80, ...},
    "strengths": ["...", "..."],
    "weaknesses": ["...", "..."],
    "recommendation": "推荐"
  }
}
```

---

## 常见问题

### Q: 启动后无法创建面试？

检查页面底部的 LLM 状态。如果是 `⚠️ LLM 未配置`，需要填写 API Key 并保存。本系统 **必须** 配置大语言模型才能运行——所有问题和追问均由 LLM 动态生成，无任何预设模板。

### Q: 如何切换不同的 LLM 提供商？

在「大语言模型配置」面板选择提供商，或通过环境变量：

```powershell
$env:LLM_PROVIDER="deepseek"    # openai / deepseek / moonshot / custom
$env:LLM_BASE_URL="https://api.deepseek.com/v1"
$env:LLM_MODEL="deepseek-chat"
```

### Q: 语音识别不能用？

- 请使用 **Chrome** 浏览器
- 确保页面加载时勾选了「启用语音交互」
- 首次使用时浏览器会请求麦克风权限，请允许

### Q: 如何对接方向一/方向二的数据？

`POST /api/interview/start` 接口接收 `profile`（人才画像）和 `candidate`（候选人档案）两个参数，格式分别对应 `profile_schema.json` 和 `candidate_schema.json`。

### Q: 端口被占用？

```powershell
taskkill /f /im python.exe   # 杀掉所有 Python 进程
python app.py                # 重新启动
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3 + Flask |
| 前端 | HTML + CSS + Vanilla JS |
| 语音 | Web Speech API（浏览器原生） |
| LLM | OpenAI 兼容接口（DeepSeek / OpenAI / Moonshot 等） |
| 存储 | JSON 文件系统 |
| 依赖 | `flask`, `openai` |

---

## 许可证

实训项目 · 仅供学习交流使用
