# AI 招聘评估系统答辩展示内容

本文档依据当前 `main` 项目代码整理，用于毕业设计、课程设计或项目验收答辩。展示重点不再停留在单一“AI 面试引擎”，而是围绕新版系统的完整招聘评估闭环：人才画像生成、简历智能解析、画像与简历数据同步、AI 动态面试、面试记录与评估。

## 1. 项目定位

本项目是一个面向招聘场景的 AI 招聘评估系统，目标是把传统招聘中分散、主观、难追溯的环节，转化为可结构化沉淀、可复用、可验证的智能评估流程。

系统解决的核心问题包括：

- 招聘需求模糊：招聘方往往只有粗略 JD，缺少清晰的人才画像、排除条件和信号维度。
- 简历信息失真：简历中存在大量主观能力声明，缺少和项目事实、成果指标的对应关系。
- 面试问题模板化：传统面试题容易与岗位和候选人脱节，无法针对简历盲点追问。
- 评估过程不可追溯：面试对话、追问依据、评分结果缺少统一沉淀。

系统最终形成一条闭环：

```text
招聘需求 / JD
  -> 对话式人才画像
  -> 简历上传与语义解析
  -> 画像与候选人格式转换
  -> AI 动态生成面试方案
  -> 语音/文字面试交互
  -> 对话记录与综合评估
```

## 2. 系统总体架构

当前项目采用 FastAPI 后端 + 原生 JavaScript SPA 前端 + JSON 文件本地存储的架构。

```text
human_analysis/
├── run.py                      # Uvicorn 启动入口
├── config.py                   # 端口、路径、LLM、GitHub Token 等统一配置
├── requirements.txt            # 项目依赖
├── app/
│   ├── main.py                 # FastAPI 应用工厂、CORS、静态资源挂载、路由注册
│   ├── routers/                # API 路由层
│   │   ├── portrait.py         # 人才画像 API
│   │   ├── resume.py           # 简历解析 API
│   │   ├── interview.py        # AI 面试 API
│   │   └── llm_config.py       # 面试 LLM 配置 API
│   ├── services/               # 业务服务层
│   │   ├── portrait/           # 招聘需求对话、JD 解析、画像生成
│   │   ├── resume/             # 文件抽取、文本清洗、语义分析、数字足迹挖掘
│   │   └── interview/          # 问题生成、追问、计时、评估、语音服务
│   ├── converters/             # 跨模块数据转换
│   ├── storage/                # JSON 文件存储
│   ├── models/                 # Pydantic 请求/响应模型
│   └── schemas/                # JSON Schema
├── frontend/
│   ├── index.html              # 单页应用入口和导航
│   ├── css/style.css           # 统一视觉样式
│   └── js/
│       ├── api.js              # 统一 API 客户端
│       ├── router.js           # hash 路由
│       ├── portrait/           # 人才画像页面
│       ├── resume/             # 简历分析页面
│       └── interview/          # 面试设置、面试房间、记录页面
└── data/
    ├── conversations/          # 画像对话历史
    ├── profiles/               # 原始人才画像
    ├── resumes/                # 简历解析结果
    ├── candidates/             # 候选人数据
    └── interviews/             # 面试画像库、候选人库、面试记录
```

后端在 `app/main.py` 中集中注册四组路由：

- `/api/portrait`：人才画像模块
- `/api/resume`：简历解析模块
- `/api/interview`：AI 面试模块
- `/api/llm`：面试大语言模型配置模块

前端通过 `frontend/index.html` 加载统一导航与各模块脚本，使用 hash 路由切换页面：

- `#/portrait`：人才画像
- `#/resume`：简历分析
- `#/interview`：面试设置
- `#/interview/:id`：面试房间
- `#/records`：面试记录

## 3. 核心业务流程

### 3.1 人才画像生成流程

人才画像模块用于把模糊招聘需求转为结构化岗位画像。

入口文件：

- 后端路由：`app/routers/portrait.py`
- Agent 服务：`app/services/portrait/agent.py`
- 提示词：`app/services/portrait/prompts.py`
- 前端页面：`frontend/js/portrait/app.js`

流程说明：

1. 用户在前端粘贴 JD 或用自然语言描述招聘需求。
2. 前端通过 `api.chat()` 调用 `/api/portrait/chat`。
3. 后端创建 `RecruitmentAgent`，调用 DeepSeek 或兼容 OpenAI 的模型。
4. Agent 根据系统提示词进行需求澄清，重点覆盖岗位背景、日常工作、选人标准、排除条件、成长路径、文化适配等维度。
5. 当用户点击“生成画像”或输入“生成画像”等关键词时，后端调用 `generate_profile()`。
6. LLM 输出结构化画像 JSON，系统执行 `enrich_profile()` 补全字段并保存对话草稿。
7. 用户确认保存后，`save_profile_endpoint()` 会：
   - 校验画像结构；
   - 保存原始画像；
   - 调用 `portrait_to_interview_profile()` 转换为面试引擎可用格式；
   - 同步写入 `data/interviews/profiles.json`。

画像结构重点字段：

- `company_context`：招聘原因、团队现状、业务背景。
- `core_roles`：岗位核心角色和关键职责。
- `signal_dimensions`：评估大类和细分信号维度。
- `must_have`：必须满足条件。
- `nice_to_have`：加分项。
- `anti_profile`：结构性不匹配画像。
- `general_questions`：面试末尾用于补齐评估信号的问题。
- `conversation_summary`：招聘方核心诉求和对话结论。

答辩展示建议：

- 展示一段 JD 输入。
- 说明系统不是简单抽取关键词，而是通过对话挖掘真实招聘需求。
- 打开生成后的画像，重点展示“信号维度”和“风险画像”。
- 强调保存画像后会自动同步到面试模块，成为后续面试问题生成的依据。

### 3.2 简历智能解析流程

简历模块负责从 PDF、Word、图片简历中抽取文本，并通过 LLM 分离“能力声明”和“客观经历”。

入口文件：

- 后端路由：`app/routers/resume.py`
- 流水线：`app/services/resume/pipeline_engine.py`
- 文件抽取：`app/services/resume/extractors.py`
- 语义分析：`app/services/resume/llm_agent.py`
- 数字足迹：`app/services/resume/github_crawler.py`
- 前端页面：`frontend/js/resume/resume.js`

处理流水线：

```text
上传文件
  -> 文件类型校验
  -> 临时保存
  -> 文本抽取
  -> 文本清洗
  -> LLM 语义分析
  -> GitHub / 博客数字足迹挖掘
  -> 保存解析结果
  -> 转换为面试候选人
  -> 同步写入候选人库
```

支持格式：

- PDF
- DOC / DOCX
- PNG / JPG / JPEG / WEBP / BMP

文本抽取策略：

- PDF 首先使用 `pdfplumber` 抽取文本。
- 如果 PDF 文本过少，说明可能是扫描件或图片型 PDF，会尝试使用 `PyMuPDF + PaddleOCR` OCR 回退。
- Word 文档优先使用 `python-docx`，失败后回退到 `mammoth`。
- 图片简历使用 PaddleOCR，未安装时系统给出警告并降级。

语义分析输出：

- `name`：候选人姓名。
- `contact`：邮箱、电话、GitHub、博客。
- `claims`：候选人的主观能力声明，并给出信号强度。
- `formatted_claims`：按后端、前端、AI、工程实践等类别规整能力。
- `objective_experiences`：客观经历，包含公司、岗位、时间、描述、STAR 完整度。
- `project_experiences`：项目经历，包含项目名、角色、技术栈、成果、原文证据。
- `suitable_roles`：适合岗位推荐。
- `interview_questions`：供面试阶段使用的辅助问题。
- `blind_spots`：需要面试官重点澄清的信息盲区。

数字足迹挖掘：

- 从简历文本中提取 GitHub 和博客链接。
- 调用 GitHub API 获取公开仓库数、followers、主要语言、最近仓库。
- 读取仓库 README，提取项目摘要和技术栈。
- 抓取博客页面标题和关键词标签。

本地规则回退：

当未配置 `RESUME_LLM_API_KEY`、`DASHSCOPE_API_KEY` 或 `OPENAI_API_KEY` 时，系统不会中断，而是使用启发式规则提取姓名、联系方式、技能声明、项目经历和盲区。这体现了系统的可用性设计：核心流程可运行，高级语义能力按配置增强。

答辩展示建议：

- 上传一份简历，展示解析进度条。
- 展示项目经历卡片、能力声明分组、适合岗位、AI 面试辅助问题。
- 强调 `blind_spots` 是后续面试追问的重要输入。
- 展示 GitHub 数字足迹，让评委看到系统不只依赖简历文本。

### 3.3 跨模块数据同步设计

新版项目的关键升级是三大模块之间不是孤立页面，而是通过转换器和统一存储形成数据闭环。

相关文件：

- `app/converters/profile_converter.py`
- `app/converters/candidate_converter.py`
- `app/storage/interview_store.py`

画像转换：

`portrait_to_interview_profile()` 将人才画像转为面试画像格式：

- `job_title` 转为 `position.title`。
- `signal_dimensions` 展开为 `requirements.skills`。
- “核心 / 重要 / 参考”权重映射为“精通 / 熟悉 / 了解”和数值权重。
- 原始画像的丰富字段保留在扩展字段中，例如：
  - `_signal_dimensions`
  - `_company_context`
  - `_must_have`
  - `_nice_to_have`
  - `_anti_profile`
  - `_general_questions`

简历转换：

`resume_to_interview_candidate()` 将简历解析结果转为候选人格式：

- `objective_experiences` 转为候选人经历。
- `claims` 和 `formatted_claims` 转为技能声明。
- GitHub、博客、适合岗位、AI 面试辅助问题放入 `external_profiles`。
- `blind_spots` 保留为 `_blind_spots`。

存储设计：

`ProfileCandidateStorage` 维护面试专用的画像库和候选人库：

- `data/interviews/profiles.json`
- `data/interviews/candidates.json`

`InterviewStorage` 维护面试记录：

- `data/interviews/index.json`
- `data/interviews/records/INT_*.json`

答辩表达重点：

> 本项目不是三个功能页面的简单拼接，而是通过标准化转换器将“招聘需求”和“候选人证据”统一成面试引擎的输入，从而让后续问题生成、追问和评估都能基于同一套结构化数据。

### 3.4 AI 动态面试流程

面试模块是整个系统的闭环执行层。

入口文件：

- 后端路由：`app/routers/interview.py`
- 面试引擎：`app/services/interview/interview_engine.py`
- 问题生成：`app/services/interview/question_generator.py`
- 追问策略：`app/services/interview/follow_up_strategy.py`
- LLM 服务：`app/services/interview/llm_service.py`
- 语音服务：`app/services/interview/speech_service.py`
- 前端设置页：`frontend/js/interview/setup.js`
- 面试房间：`frontend/js/interview/room.js`
- 面试记录：`frontend/js/interview/records.js`

面试启动流程：

1. 用户进入 `#/interview`。
2. 页面加载面试画像列表和候选人列表。
3. 用户必须选择一个人才画像和一个简历分析结果。
4. 用户设置面试时长，默认 45 分钟。
5. 前端调用 `/api/interview/start`。
6. 后端根据 `profile_id` 和 `candidate_id` 读取结构化数据。
7. `InterviewEngine.start_interview()` 调用 `QuestionGenerator.generate_plan()`。
8. LLM 根据岗位画像、简历证据、简历盲点和外部足迹生成面试方案。
9. 系统创建 `INT_XXXXXXXX` 面试记录并保存。
10. 前端跳转到 `#/interview/:id` 面试房间。

动态问题生成依据：

- 岗位名称、部门、职级、薪资范围。
- 学历、年限、技能、软技能、加分项。
- 画像信号维度。
- 必须验证项。
- 加分信号。
- 风险画像。
- 画像建议问题。
- 候选人工作经历、教育背景、技能声明。
- 外部信号，例如 GitHub 活跃度和仓库。
- 简历盲点，例如项目缺少指标或贡献边界不清。

LLM 生成的面试方案格式：

- `sections`：面试环节列表。
- 每个环节包含：
  - `section_name`
  - `duration_minutes`
  - `focus_area`
  - `questions`
- 每个问题包含：
  - `question_id`
  - `question_text`
  - `category`
  - `difficulty`
  - `expected_answer_keywords`
  - `follow_up_triggers`

追问逻辑：

候选人提交回答后，系统调用 `process_answer()`：

1. 保存候选人回答。
2. 根据当前问题和回答内容调用 `FollowUpStrategy.generate_follow_up()`。
3. LLM 判断回答是否具体、可信、有过程和结果。
4. 如果回答泛泛、缺少细节，则生成一个不超过 30 个汉字的自然追问。
5. 每个问题最多追问 2 次，避免无限追问。

时间控制：

`TimeController` 根据 LLM 生成的环节时长管理进度：

- 计算当前所处面试环节。
- 计算剩余时间。
- 判断是否需要收尾。
- 根据进度建议“正常继续”“加快速度”“深入追问”“精简问题”“紧急收尾”。

面试结束与评估：

结束面试后，`InterviewEngine.end_interview()` 会：

- 写入结束时间。
- 标记状态为“已完成”。
- 调用 `_generate_evaluation()` 生成评估结果。
- 保存完整面试记录。

评估结果包括：

- `overall_score`：综合评分。
- `dimension_scores`：技术能力、项目经验、沟通表达、文化契合。
- `strengths`：优势。
- `weaknesses`：不足。
- `recommendation`：强烈推荐、推荐、待定、不推荐。
- `ai_comment`：综合评价。

如果 LLM 不可用，系统会保存记录并给出待人工审核的回退评估，保证业务流程不中断。

### 3.5 LLM 配置和多模型兼容

系统中有两类 LLM 配置：

1. 画像模块配置：
   - API Key 存在浏览器 localStorage。
   - 默认使用 `PORTRAIT_LLM_BASE_URL` 和 `PORTRAIT_LLM_MODEL`。
   - 默认模型为 DeepSeek。

2. 简历与面试后端配置：
   - 简历模块读取环境变量：
     - `RESUME_LLM_API_KEY`
     - `DASHSCOPE_API_KEY`
     - `OPENAI_API_KEY`
   - 面试模块通过 `/api/llm/config` 保存到 `.env.json`。
   - 前端支持 OpenAI、九安 AI Gateway、DeepSeek、Moonshot、自定义兼容接口。

LLM 服务抽象：

`app/services/interview/llm_service.py` 使用 OpenAI SDK 的兼容接口封装：

- `chat()`：普通文本生成。
- `chat_json()`：JSON 结构化生成。
- `generate_follow_up()`：根据回答生成追问。
- `evaluate_interview()`：根据面试记录生成评价。
- `reload_llm_service()`：保存配置并重新加载服务。

答辩表达重点：

> 系统没有把模型供应商写死，而是使用 OpenAI SDK 兼容接口进行抽象，前端可以切换不同供应商和模型，因此具备较好的扩展性。

### 3.6 语音交互设计

语音功能集中在面试房间：

- 前端 `room.js` 使用浏览器 `SpeechRecognition` 实现实时语音输入。
- 后端 `speech_service.py` 支持阿里云 NLS TTS 和 ASR。
- 如果未配置阿里云凭证，系统自动降级为文字面试，不影响主流程。

语音 API：

- `POST /api/interview/tts`：文本转语音。
- `POST /api/interview/asr`：上传音频转文字。
- `GET /api/interview/voices`：获取可用发音人和配置状态。

阿里云 NLS 配置项：

- `ALIYUN_NLS_AK_ID`
- `ALIYUN_NLS_AK_SECRET`
- `ALIYUN_NLS_APP_KEY`
- `ALIYUN_NLS_REGION`

也可以在 `.env.json` 中配置 `aliyun_nls`。

本项目对语音依赖做了可选降级：

- 没有安装 `aliyun-python-sdk-core` 时，服务仍然可以启动。
- 没有配置阿里云 NLS 时，TTS/ASR 接口返回明确提示。
- 浏览器不支持语音识别时，用户可以手动输入答案。

## 4. 技术亮点

### 4.1 从“关键词匹配”升级为“证据驱动评估”

系统不是仅判断简历是否包含某个技能词，而是区分：

- 候选人的主观声明；
- 能被项目经历支撑的客观事实；
- GitHub / 博客等外部证据；
- 缺少证据的信息盲区。

这些信息共同参与面试问题生成，使问题更接近真实招聘评估。

### 4.2 岗位画像与候选人证据双输入

面试问题不是固定题库，而是由两个输入共同决定：

- 岗位画像：决定“应该考察什么”。
- 简历分析：决定“应该验证什么”。

这种设计减少了通用模板题，提高了问题和岗位、候选人的相关性。

### 4.3 全流程数据可追溯

系统保存：

- 画像对话历史；
- 结构化人才画像；
- 简历解析结果；
- 候选人档案；
- 面试方案；
- 候选人回答；
- AI 追问；
- 最终评估。

这使得一次招聘评估可以被复盘，而不是只留下主观结论。

### 4.4 LLM 失败回退机制

项目对外部依赖做了多层降级：

- 简历 LLM 不可用时使用本地启发式规则。
- OCR 未安装时只影响图片解析，不影响普通 PDF/Word。
- 阿里云语音未配置时降级为文字交互。
- 面试评估 LLM 不可用时仍保存记录并给出待人工审核结果。

### 4.5 前后端职责清晰

后端负责：

- 数据校验；
- 文件解析；
- LLM 调用；
- 格式转换；
- 面试状态和记录保存。

前端负责：

- SPA 路由；
- 上传、选择、面试交互；
- 配置面板；
- 进度和结果展示；
- 浏览器语音输入。

## 5. 演示路线

建议答辩现场按以下顺序演示，时间控制在 8 到 12 分钟。

### 第一步：启动系统

```bash
python run.py
```

访问：

```text
http://127.0.0.1:8000
```

说明启动后后端会挂载前端 SPA，并提供 `/health` 健康检查接口。

### 第二步：展示人才画像

演示内容：

1. 进入“人才画像”页面。
2. 设置 DeepSeek API Key。
3. 粘贴一段招聘 JD。
4. 与 AI 对话补充团队背景、排除条件、工作方式。
5. 点击“生成画像”。
6. 展示结构化画像。
7. 点击“保存”。

讲解重点：

- 对话式需求澄清。
- 信号维度不是固定模板，而是随岗位生成。
- 保存后自动转换并同步到面试画像库。

### 第三步：展示简历分析

演示内容：

1. 进入“简历分析”页面。
2. 上传 PDF 或 DOCX 简历。
3. 查看解析结果。
4. 展示项目经历、能力声明、适合岗位、AI 面试辅助问题、信息盲区。
5. 如果简历中有 GitHub 链接，展示数字足迹。

讲解重点：

- 文件抽取支持多格式。
- LLM 分离“声明”和“事实”。
- 信息盲区会进入面试问题设计。
- 解析成功后自动同步到候选人库。

### 第四步：展示 AI 面试设置

演示内容：

1. 进入“AI 面试”页面。
2. 选择刚保存的人才画像。
3. 选择刚解析的简历候选人。
4. 配置 LLM。
5. 设置面试时长。
6. 点击“开始 AI 面试”。

讲解重点：

- 当前新版系统不再支持手动填写预设岗位，而是强制使用画像和简历结果作为输入。
- 这样可以保证面试问题有明确来源和证据。

### 第五步：展示面试房间

演示内容：

1. 展示面试方案侧边栏。
2. AI 自动提问。
3. 输入或语音回答。
4. 展示 AI 根据回答生成追问。
5. 展示计时、进度条、当前环节。
6. 点击结束面试。

讲解重点：

- 面试问题由 LLM 基于画像和简历动态生成。
- 每个问题最多追问 2 次，避免失控。
- 时间控制会提示收尾。
- TTS/ASR 可选，不配置也可文字演示。

### 第六步：展示面试记录和评估

演示内容：

1. 进入“面试记录”页面。
2. 打开刚完成的面试。
3. 展示完整对话和 AI 评估。
4. 展示重新开始面试功能。

讲解重点：

- 面试全过程被结构化保存。
- 评估结论不是孤立输出，而是基于完整对话记录。
- 记录可以复盘、删除或重启。

## 6. API 展示清单

### 人才画像 API

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/portrait/chat` | 与画像 Agent 对话 |
| POST | `/api/portrait/parse-jd` | 解析 JD |
| POST | `/api/portrait/generate-profile` | 生成结构化画像 |
| POST | `/api/portrait/save-profile` | 保存画像并同步到面试画像库 |
| GET | `/api/portrait/profiles` | 查询画像列表 |
| GET | `/api/portrait/conversations` | 查询对话历史 |

### 简历 API

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/resume/parse` | 上传并解析简历 |
| GET | `/api/resume/results` | 查询简历解析结果 |
| GET | `/api/resume/results/{resume_id}` | 查看解析详情 |
| DELETE | `/api/resume/results/{resume_id}` | 删除解析结果 |

### 面试 API

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/interview/start` | 根据画像和候选人开始面试 |
| POST | `/api/interview/next-question` | 获取当前时间段的下一个问题 |
| POST | `/api/interview/answer` | 提交候选人回答 |
| POST | `/api/interview/ask-follow-up` | 保存 AI 追问 |
| POST | `/api/interview/end` | 结束面试并生成评估 |
| POST | `/api/interview/status` | 获取时间与环节状态 |
| GET | `/api/interview/list` | 查询面试记录 |
| GET | `/api/interview/detail/{interview_id}` | 查看面试详情 |
| POST | `/api/interview/restart/{interview_id}` | 从历史记录重新开始 |
| GET | `/api/interview/profiles` | 查询可用于面试的画像 |
| GET | `/api/interview/candidates` | 查询可用于面试的候选人 |
| POST | `/api/interview/tts` | 文本转语音 |
| POST | `/api/interview/asr` | 音频转文字 |
| GET | `/api/interview/voices` | 查询语音配置状态 |

### LLM 配置 API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/llm/config` | 获取当前配置 |
| POST | `/api/llm/config` | 保存 LLM 配置 |
| POST | `/api/llm/test` | 测试连接 |
| POST | `/api/llm/toggle` | 启用或禁用 LLM 增强 |

## 7. 关键代码讲解

### 7.1 应用工厂

`app/main.py` 中的 `create_app()` 完成：

- 创建 FastAPI 应用；
- 配置跨域；
- 添加静态资源不缓存中间件；
- 注册四个业务路由；
- 挂载 `frontend` 静态文件；
- 为 `/` 返回 SPA 入口；
- 提供 `/health` 健康检查。

### 7.2 简历流水线

`ResumePipelineEngine.run_pipeline()` 是简历模块主流程：

- 根据后缀选择 PDF、Word、图片解析器。
- 文本为空时返回失败结果。
- 清洗文本后调用语义分析。
- 挖掘数字足迹。
- 输出包含阶段状态、耗时、文本长度的完整结果。

### 7.3 问题生成器

`QuestionGenerator.generate_plan()` 强制要求 LLM 可用，并基于结构化画像和候选人数据生成面试方案。

值得强调的是，生成 prompt 中显式加入了：

- 画像信号维度；
- 必须验证项；
- 风险画像；
- 候选人经历；
- 外部信号；
- 简历盲点。

这保证了问题不是通用模板题。

### 7.4 面试引擎

`InterviewEngine` 是面试状态管理核心：

- `start_interview()`：生成计划并创建面试记录。
- `get_next_question()`：根据当前时间和已问问题返回下一个问题。
- `process_answer()`：保存回答并判断是否追问。
- `ask_follow_up()`：保存 AI 追问。
- `end_interview()`：结束面试并生成评估。
- `get_time_status()`：返回进度、剩余时间、收尾建议。

### 7.5 数据转换器

转换器是新版系统的重要连接层：

- `portrait_to_interview_profile()` 把岗位画像转为面试画像。
- `resume_to_interview_candidate()` 把简历解析结果转为候选人档案。

这两个转换器让画像模块和简历模块的输出可以被面试模块直接消费。

## 8. 答辩讲稿示例

开场：

> 我做的是一个 AI 招聘评估系统。它不是单纯的简历解析工具，也不是一个固定题库面试工具，而是把招聘流程中的人才画像、简历证据和面试评估连接起来，形成一个可追溯的智能招聘闭环。

架构介绍：

> 系统后端使用 FastAPI，前端是原生 JavaScript SPA。后端按业务划分为画像、简历、面试和 LLM 配置四组 API。数据暂时采用 JSON 文件存储，便于本地演示和调试。系统核心逻辑都在 services 层，routers 只负责请求入口和错误处理。

画像模块：

> 人才画像模块的目标是解决“招聘需求不清楚”的问题。用户可以粘贴 JD，也可以和 AI 逐步对话。Agent 会围绕岗位背景、日常工作、选人标准和排除条件进行澄清，最后生成包含信号维度、必须条件、加分项和风险画像的结构化 JSON。

简历模块：

> 简历模块不是简单抽文本，而是将候选人的主观能力声明和客观项目经历分离。系统会给能力声明和项目事实打信号强度，并识别简历盲点，例如项目没有说明技术栈、没有指标、没有个人贡献边界。同时系统会挖掘 GitHub 和博客等外部足迹。

面试模块：

> 面试模块使用画像和简历两个结构化输入生成问题。画像决定要考察什么，简历决定要验证什么。面试过程中，AI 会根据候选人的回答判断是否需要追问。回答过于笼统时，系统会生成短追问，每个问题最多追问两次。

总结：

> 这个系统的核心价值是让招聘评估从“凭感觉判断”变为“基于画像、证据和对话记录判断”。它保留了 AI 的灵活性，同时用结构化数据和记录沉淀保证可追溯。

## 9. 常见答辩问题与回答

### Q1：为什么不用传统固定题库？

固定题库难以覆盖不同岗位和不同候选人的差异。本项目的问题由岗位画像和候选人简历共同决定，可以针对具体经历、具体盲点和具体岗位信号生成问题，更接近真实面试。

### Q2：LLM 输出不稳定怎么办？

系统要求 LLM 严格返回 JSON，并在代码中做了解析、校验和字段规范化。简历模块在 LLM 不可用或返回异常时会使用本地启发式规则回退；面试评估不可用时仍保存记录并交由人工审核。

### Q3：如何保证面试追问不会无限进行？

`InterviewEngine.process_answer()` 中为每个 `question_id` 维护追问次数，单个问题最多追问 2 次。同时追问由 LLM 判断回答是否具体，回答已经有过程和结果时不追问。

### Q4：系统如何处理没有 API Key 的情况？

不同模块有不同降级策略。画像模块需要用户配置 API Key 才能对话；简历模块没有 LLM Key 时使用本地规则回退；语音服务未配置时降级为文字面试；面试模块会提示用户配置 LLM，因为问题生成依赖模型。

### Q5：为什么使用 JSON 文件存储？

本项目当前定位是原型系统和答辩演示，JSON 文件便于调试、查看和迁移。存储层已经封装在 `app/storage` 中，后续可以替换为 SQLite、PostgreSQL 或 MongoDB，而不会大幅影响业务服务层。

### Q6：如何扩展到企业级使用？

可从四方面扩展：

- 存储层替换为数据库，并加入用户、权限和租户隔离。
- 接入企业 ATS 或 HR 系统。
- 增加评估模板版本管理和模型输出审计。
- 引入人工复核流程，避免完全自动化决策。

### Q7：项目最大的创新点是什么？

最大创新点是把人才画像、简历证据和面试评估连接成闭环。系统不是只做一个 AI 聊天页面，而是让前一阶段的结构化输出成为后一阶段的输入，最终形成可追溯的招聘评估链路。

## 10. 后续优化方向

- 引入数据库和用户权限，支持多招聘项目并行管理。
- 为画像、简历和面试结果增加版本号和审计记录。
- 增加批量简历解析和候选人排序。
- 增加可配置评分 Rubric，让企业可以自定义评价维度。
- 将面试问题和追问与画像信号维度建立更明确的覆盖率统计。
- 引入人工复核页面，降低 AI 评估的误判风险。
- 将语音服务抽象为多供应商接口，支持阿里云、Azure、浏览器原生等多种方案。

## 11. 一页式总结

项目名称：AI 招聘评估系统

技术栈：FastAPI、原生 JavaScript SPA、OpenAI SDK 兼容接口、PDF/Word/OCR 文本抽取、GitHub API、JSON 本地存储。

核心模块：

- 人才画像：通过对话生成结构化岗位画像。
- 简历分析：解析简历，分离声明与事实，挖掘外部足迹。
- AI 面试：结合画像和简历动态生成问题、追问和评估。
- LLM 配置：支持多模型和兼容接口切换。

核心价值：

- 让招聘需求更清晰；
- 让简历分析更可验证；
- 让面试问题更贴合岗位和候选人；
- 让面试过程和评估结果可追溯。
