# AI 招聘评估系统答辩展示页

本文档依据当前项目代码整理，面向毕业设计、课程设计或项目验收展示。内容聚焦系统本身的设计、实现、优势和应用价值。

## 1. 项目概述

AI 招聘评估系统是一个面向招聘评估场景的智能化原型系统。系统将招聘需求、候选人简历、外部数字足迹和面试过程统一纳入结构化数据流，通过大语言模型完成岗位画像生成、简历语义解析、动态面试提问、追问和评估记录沉淀。

系统由三类核心数据驱动：

- 岗位画像：描述企业真正需要考察的能力、职责、风险画像和加分信号。
- 候选人证据：来自简历、项目经历、能力声明、GitHub 和博客等外部足迹。
- 面试过程记录：包含问题、回答、追问、时间状态和最终评价。

系统形成的完整链路如下：

```text
招聘需求 / JD
  -> 对话式岗位画像
  -> 简历上传与语义解析
  -> 候选人证据结构化
  -> 画像与简历同步到面试引擎
  -> AI 动态生成面试方案
  -> 语音或文字面试交互
  -> 面试记录与综合评估
```

## 2. 要解决的问题

### 2.1 招聘需求难以结构化

传统招聘中，岗位要求常以 JD 或口头描述存在，容易停留在“熟悉 Java”“沟通能力好”“有项目经验”等宽泛表述。系统通过画像 Agent 引导招聘方补充岗位背景、团队现状、核心职责、必须条件、加分项和排除画像，将模糊需求转换为可被后续模块消费的结构化画像。

### 2.2 简历内容难以验证

简历中通常混合了能力声明、项目经历和主观描述。系统不是只做文本抽取，而是将候选人的主观能力声明与客观经历分离，并识别项目中的成果指标、个人贡献、技术栈和信息盲区，为面试阶段提供可验证的证据点。

### 2.3 面试问题与候选人脱节

固定题库难以覆盖不同岗位和不同候选人的差异。系统通过岗位画像和候选人证据共同生成面试方案，使问题能够围绕岗位信号维度、简历经历、风险点和待澄清信息展开。

### 2.4 评估过程缺少沉淀

传统面试容易只留下最终主观结论。系统保存画像、简历解析、面试方案、候选人回答、AI 追问和最终评价，使招聘评估过程可以复盘、比较和持续优化。

## 3. 系统架构

当前项目采用 FastAPI 后端、原生 JavaScript SPA 前端和 JSON 文件本地存储。整体目录如下：

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

后端在 `app/main.py` 中注册四组业务路由：

- `/api/portrait`：人才画像模块。
- `/api/resume`：简历解析模块。
- `/api/interview`：AI 面试模块。
- `/api/llm`：大语言模型配置模块。

前端使用 hash 路由切换页面：

- `#/portrait`：人才画像。
- `#/resume`：简历分析。
- `#/interview`：AI 面试设置。
- `#/interview/:id`：面试房间。
- `#/records`：面试记录。

## 4. 核心模块

### 4.1 人才画像模块

人才画像模块用于将招聘需求转换成结构化岗位画像。核心文件包括：

- `app/routers/portrait.py`
- `app/services/portrait/agent.py`
- `app/services/portrait/prompts.py`
- `frontend/js/portrait/app.js`
- `frontend/js/portrait/chat.js`
- `frontend/js/portrait/profile.js`

模块能力：

- 支持用户粘贴 JD 或通过自然语言描述招聘需求。
- 支持对话式需求澄清，覆盖岗位背景、团队现状、核心职责、选人标准和排除条件。
- 支持 JD 解析和画像生成两个路径。
- 支持生成结构化画像 JSON。
- 支持画像保存后自动同步到面试画像库。

画像结构包含：

- `company_context`：招聘原因、团队现状、业务背景。
- `core_roles`：岗位核心角色和关键职责。
- `signal_dimensions`：评估大类和细分信号维度。
- `must_have`：必须满足条件。
- `nice_to_have`：加分项。
- `anti_profile`：结构性不匹配画像。
- `general_questions`：面试末尾可用于补齐评估信号的问题。
- `conversation_summary`：招聘诉求和对话结论。

技术实现上，`RecruitmentAgent` 通过 OpenAI SDK 兼容接口调用画像模型，并提供以下能力：

- 历史对话压缩：长对话只保留最近消息，同时把早期对话摘要作为上下文，降低上下文长度压力。
- 画像草稿上下文注入：已有岗位、招聘原因、必要条件和排除条件会进入后续对话。
- JSON 提取容错：支持从纯 JSON、Markdown 代码块和混合文本中提取画像 JSON。
- 失败重试：画像生成失败时会用更严格的 JSON-only 提示词再次生成。

### 4.2 简历智能解析模块

简历模块负责从多格式文件中提取文本，并将候选人信息转换为可用于面试的结构化证据。核心文件包括：

- `app/routers/resume.py`
- `app/services/resume/pipeline_engine.py`
- `app/services/resume/extractors.py`
- `app/services/resume/cleaner.py`
- `app/services/resume/llm_agent.py`
- `app/services/resume/github_crawler.py`
- `frontend/js/resume/resume.js`

解析流水线：

```text
上传文件
  -> 文件格式校验
  -> 临时保存
  -> 文本抽取
  -> 文本清洗
  -> LLM 语义分析
  -> GitHub / 博客数字足迹挖掘
  -> 保存解析结果
  -> 转换为面试候选人
  -> 同步写入候选人库
```

支持文件格式：

- PDF。
- DOC / DOCX。
- PNG / JPG / JPEG / WEBP / BMP。

文本抽取策略：

- PDF 优先使用 `pdfplumber` 抽取文本。
- 图片型 PDF 或文本过少的 PDF 会尝试使用 `PyMuPDF + PaddleOCR` 进行 OCR 回退。
- Word 文档优先使用 `python-docx`，失败后回退到 `mammoth`。
- 图片简历使用 PaddleOCR，未安装时功能降级但服务仍可运行。

语义分析输出：

- `name`：候选人姓名。
- `contact`：邮箱、电话、GitHub、博客。
- `claims`：候选人的主观能力声明。
- `formatted_claims`：按后端、前端、AI、工程实践等类别规整的能力声明。
- `objective_experiences`：客观工作或实习经历。
- `project_experiences`：项目经历、角色、技术栈、成果和原文证据。
- `suitable_roles`：适合岗位推荐。
- `interview_questions`：面试阶段可使用的辅助问题。
- `blind_spots`：需要面试官澄清的信息盲区。
- `digital_footprint`：GitHub、仓库、博客等外部足迹。

数字足迹挖掘能力：

- 从简历文本提取 GitHub 和博客链接。
- 读取 GitHub 公开仓库数、followers、主要语言和最近仓库。
- 抽取仓库 README 摘要和技术栈线索。
- 抓取博客标题和关键词标签。

可用性设计：

- 未配置简历 LLM Key 时，系统仍可使用本地启发式规则提取关键信息。
- OCR 可选，不影响普通 PDF 和 Word 文件解析。
- 每次解析会输出处理阶段、耗时和文本长度，便于调试和展示系统运行过程。

### 4.3 跨模块数据同步

本项目的重要设计是三大模块不是孤立页面，而是通过转换器和统一存储形成数据闭环。核心文件包括：

- `app/converters/profile_converter.py`
- `app/converters/candidate_converter.py`
- `app/storage/interview_store.py`

画像转换：

`portrait_to_interview_profile()` 将人才画像转换为面试画像格式：

- `job_title` 转为 `position.title`。
- `signal_dimensions` 展开为 `requirements.skills`。
- “核心 / 重要 / 参考”权重映射为“精通 / 熟悉 / 了解”和数值权重。
- 原始画像的丰富字段保留在扩展字段中，例如 `_signal_dimensions`、`_company_context`、`_must_have`、`_nice_to_have`、`_anti_profile`、`_general_questions`。

简历转换：

`resume_to_interview_candidate()` 将简历解析结果转换为候选人格式：

- `objective_experiences` 转为候选人经历。
- `claims` 和 `formatted_claims` 转为技能声明。
- GitHub、博客、适合岗位和辅助问题写入 `external_profiles`。
- `blind_spots` 保留为 `_blind_spots`，供面试问题生成使用。

统一存储：

- `data/interviews/profiles.json`：面试画像库。
- `data/interviews/candidates.json`：面试候选人库。
- `data/interviews/index.json`：面试记录索引。
- `data/interviews/records/INT_*.json`：单场面试详情。

这一设计使画像模块的输出和简历模块的输出能够自动成为面试模块的输入，减少重复录入，也保证面试问题有明确的数据来源。

### 4.4 AI 动态面试模块

面试模块是系统闭环的执行层。核心文件包括：

- `app/routers/interview.py`
- `app/services/interview/interview_engine.py`
- `app/services/interview/question_generator.py`
- `app/services/interview/follow_up_strategy.py`
- `app/services/interview/llm_service.py`
- `app/services/interview/speech_service.py`
- `frontend/js/interview/setup.js`
- `frontend/js/interview/room.js`
- `frontend/js/interview/records.js`

面试启动条件：

- 必须选择已保存的人才画像。
- 必须选择已解析的候选人简历结果。
- 必须配置可用的面试 LLM。
- 可设置面试总时长，默认 45 分钟。

问题生成依据：

- 岗位名称、部门、职级、薪资范围。
- 学历、年限、技能和软技能要求。
- 画像信号维度。
- 必须验证项。
- 加分信号。
- 风险画像。
- 画像建议问题。
- 候选人工作经历、教育背景和技能声明。
- GitHub、博客等外部信号。
- 简历盲点。

面试方案结构：

- `sections`：面试环节列表。
- `section_name`：环节名称。
- `duration_minutes`：环节时长。
- `focus_area`：考察重点。
- `questions`：问题列表。
- `question_id`：问题编号。
- `question_text`：问题内容。
- `category`：技术、项目经验、软技能、文化契合或行为。
- `difficulty`：简单、中等或困难。
- `expected_answer_keywords`：预期关键词。
- `follow_up_triggers`：追问触发线索。

追问机制：

- 候选人提交回答后，`InterviewEngine.process_answer()` 会保存回答。
- `FollowUpStrategy.generate_follow_up()` 根据原问题、回答内容、岗位画像和对话历史判断是否追问。
- 回答过于笼统、缺少过程、缺少指标或缺少个人贡献时，会生成短追问。
- 单个问题最多追问 2 次，避免追问失控。

时间控制：

`TimeController` 根据 LLM 生成的环节时长管理面试进度：

- 计算当前所处面试环节。
- 计算剩余时间。
- 判断是否进入收尾阶段。
- 根据进度给出“正常继续”“加快速度”“深入追问”“精简问题”“紧急收尾”等建议。

面试评估：

面试结束后，`InterviewEngine.end_interview()` 会：

- 写入结束时间。
- 标记状态为“已完成”。
- 调用 LLM 生成综合评估。
- 保存完整面试记录。

评估结果包括：

- `overall_score`：综合评分。
- `dimension_scores`：技术能力、项目经验、沟通表达、文化契合。
- `strengths`：候选人优势。
- `weaknesses`：候选人不足。
- `recommendation`：强烈推荐、推荐、待定或不推荐。
- `ai_comment`：综合评价。

如果评估 LLM 不可用，系统仍会保存面试记录，并给出待人工审核的回退评估。

### 4.5 语音交互模块

语音功能主要服务于面试房间：

- 前端 `room.js` 使用浏览器 `SpeechRecognition` 进行实时语音输入。
- 后端 `speech_service.py` 支持阿里云 NLS TTS 和 ASR。
- 如果未配置阿里云凭证，系统会降级为文字交互。

语音 API：

- `POST /api/interview/tts`：文本转语音。
- `POST /api/interview/asr`：上传音频转文字。
- `GET /api/interview/voices`：获取可用发音人和配置状态。

阿里云 NLS 配置项：

- `ALIYUN_NLS_AK_ID`
- `ALIYUN_NLS_AK_SECRET`
- `ALIYUN_NLS_APP_KEY`
- `ALIYUN_NLS_REGION`

## 5. 项目优势

### 5.1 从“关键词匹配”升级为“证据驱动”

系统不只判断简历是否出现某个技能词，而是同时分析能力声明、客观项目、外部足迹和信息盲区。这样能降低简历包装带来的干扰，让面试更关注可验证证据。

### 5.2 岗位画像与候选人证据双输入

面试问题不是固定题库，也不是只由 JD 生成。系统同时使用岗位画像和候选人简历，既保证问题覆盖企业真正关心的能力维度，也保证问题能针对候选人的实际经历展开。

### 5.3 全流程可追溯

系统保存从画像对话到面试评估的完整数据链路。一次评估不是孤立结论，而是可以回看画像依据、简历证据、问题来源、回答内容和最终评分。

### 5.4 模块边界清晰，便于扩展

项目按 routers、services、converters、storage、models 分层：

- 路由层负责 API 入口。
- 服务层负责核心业务逻辑。
- 转换层负责模块间数据格式适配。
- 存储层负责数据读写。
- 模型层负责请求和响应结构。

这种结构使后续替换数据库、接入企业 ATS、扩展评分模型或切换 LLM 供应商更加容易。

### 5.5 多模型兼容

系统使用 OpenAI SDK 兼容接口封装 LLM 调用，支持 DeepSeek、OpenAI 兼容网关、九安 AI Gateway、Moonshot 等模型服务。面试模块还提供前端配置页面，可保存和测试模型连接。

### 5.6 具备失败降级能力

系统对外部依赖做了多层降级：

- 简历 LLM 不可用时使用本地启发式规则。
- OCR 未安装时不影响普通 PDF 和 Word 解析。
- 语音服务未配置时降级为文字面试。
- 面试评估失败时仍保存记录并交由人工审核。

### 5.7 更适合真实招聘复盘

传统面试记录常只有简短评价，难以判断评价是否合理。本项目保留问题、回答、追问和评估结果，并把问题与画像、简历、盲点关联起来，更适合招聘复盘、面试官校准和后续模型优化。

## 6. 应用价值

### 6.1 对招聘方

- 将模糊岗位需求转换为统一画像。
- 降低不同面试官之间的评估口径差异。
- 减少重复设计面试题的成本。
- 通过结构化记录提升复盘效率。

### 6.2 对面试官

- 快速看到候选人的能力声明、客观经历和盲点。
- 基于候选人真实经历提问，减少模板化问题。
- 使用追问机制验证项目细节、个人贡献和结果指标。
- 在面试结束后获得可参考的结构化评估。

### 6.3 对候选人

- 面试问题更贴近个人经历和目标岗位。
- 面试过程更透明，问题来源更清晰。
- 能减少与岗位无关的泛化提问。

### 6.4 对系统建设

- 数据结构清晰，便于后续接入数据库。
- API 边界明确，便于前后端独立迭代。
- 模型供应商不被写死，便于迁移和成本控制。
- JSON Schema 和 Pydantic 模型为数据规范化提供基础。

## 7. 技术实现亮点

### 7.1 FastAPI 应用工厂

`app/main.py` 中的 `create_app()` 完成：

- 创建 FastAPI 应用。
- 配置 CORS。
- 添加静态资源不缓存中间件。
- 注册画像、简历、面试和 LLM 配置路由。
- 挂载 `frontend` 静态文件。
- 为 `/` 返回 SPA 入口。
- 提供 `/health` 健康检查。

### 7.2 简历解析流水线

`ResumePipelineEngine.run_pipeline()` 将简历解析拆成明确阶段：

- 文件类型识别。
- PDF、Word 或图片文本抽取。
- 文本清洗。
- LLM 语义分析。
- 数字足迹挖掘。
- 输出处理阶段、耗时和文本长度。

### 7.3 问题生成器

`QuestionGenerator.generate_plan()` 强制使用人才画像和候选人数据生成面试方案。Prompt 中显式加入画像信号维度、必须验证项、风险画像、候选人经历、外部信号和简历盲点，保证问题不是通用模板。

### 7.4 面试状态管理

`InterviewEngine` 负责面试生命周期：

- `start_interview()`：生成计划并创建面试记录。
- `get_next_question()`：根据当前时间和已问问题返回下一个问题。
- `process_answer()`：保存回答并判断是否追问。
- `ask_follow_up()`：保存 AI 追问。
- `end_interview()`：结束面试并生成评估。
- `get_time_status()`：返回进度和剩余时间。

### 7.5 数据转换器

转换器是系统闭环的关键：

- `portrait_to_interview_profile()`：将岗位画像转换为面试画像。
- `resume_to_interview_candidate()`：将简历解析结果转换为候选人档案。

这两个转换器让前序模块的输出可以直接被面试引擎消费。

### 7.6 LLM 配置服务

`app/services/interview/llm_service.py` 封装模型调用：

- `chat()`：普通文本生成。
- `chat_json()`：结构化 JSON 生成。
- `generate_follow_up()`：生成追问。
- `evaluate_interview()`：生成面试评价。
- `reload_llm_service()`：重新加载配置。

## 8. API 展示清单

### 人才画像 API

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/portrait/chat` | 与画像 Agent 对话 |
| POST | `/api/portrait/parse-jd` | 解析 JD |
| POST | `/api/portrait/generate-profile` | 生成结构化画像 |
| POST | `/api/portrait/save-profile` | 保存画像并同步到面试画像库 |
| GET | `/api/portrait/profiles` | 查询画像列表 |
| GET | `/api/portrait/profiles/{id}` | 查询画像详情 |
| GET | `/api/portrait/conversations` | 查询对话历史 |
| GET | `/api/portrait/conversations/{id}` | 查询对话详情 |

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
| POST | `/api/interview/next-question` | 获取下一个问题 |
| POST | `/api/interview/answer` | 提交候选人回答 |
| POST | `/api/interview/ask-follow-up` | 保存 AI 追问 |
| POST | `/api/interview/end` | 结束面试并生成评估 |
| POST | `/api/interview/status` | 获取时间与环节状态 |
| GET | `/api/interview/list` | 查询面试记录 |
| GET | `/api/interview/detail/{interview_id}` | 查看面试详情 |
| DELETE | `/api/interview/detail/{interview_id}` | 删除面试记录 |
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

## 9. 数据流转细节

### 9.1 画像到面试

用户保存画像后，系统会保存原始画像，并调用 `portrait_to_interview_profile()` 生成面试画像。面试画像写入 `data/interviews/profiles.json`，之后可在面试设置页直接选择。

### 9.2 简历到候选人

用户上传简历后，系统执行完整解析流水线。解析成功后调用 `resume_to_interview_candidate()`，将简历结果转换为候选人档案，并写入 `data/interviews/candidates.json`。

### 9.3 面试到记录

开始面试后，系统生成 `INT_XXXXXXXX` 格式的面试 ID。面试记录包含：

- 候选人基本引用。
- 面试开始时间和结束时间。
- 面试状态。
- LLM 生成的面试方案。
- 候选人回答。
- AI 追问。
- 追问次数。
- 原始画像和候选人数据快照。
- 综合评估结果。

## 10. 可扩展方向

- 将 JSON 文件存储替换为 SQLite、PostgreSQL 或 MongoDB。
- 增加用户体系、权限控制和租户隔离。
- 接入企业 ATS 或 HR 系统。
- 增加批量简历解析和候选人排序。
- 增加画像、简历和面试结果的版本号。
- 增加可配置评分 Rubric。
- 增加画像信号维度覆盖率统计。
- 引入人工复核页面，降低 AI 自动评估误判风险。
- 将语音服务抽象为多供应商接口。
- 增加模型输出审计和提示词版本管理。

## 11. 一页式总结

项目名称：AI 招聘评估系统

技术栈：FastAPI、原生 JavaScript SPA、OpenAI SDK 兼容接口、PDF/Word/OCR 文本抽取、GitHub API、JSON 本地存储。

核心模块：

- 人才画像：通过对话生成结构化岗位画像。
- 简历分析：解析简历，分离能力声明与客观经历，挖掘外部足迹。
- AI 面试：结合岗位画像和候选人证据动态生成问题、追问和评估。
- LLM 配置：支持多模型和兼容接口切换。

核心优势：

- 将模糊招聘需求结构化。
- 将简历内容拆解为可验证证据。
- 将面试问题绑定岗位画像和候选人经历。
- 将面试过程完整记录并可复盘。
- 将多个 AI 能力整合为完整招聘评估闭环。

系统价值：

- 让招聘评估更一致。
- 让面试问题更相关。
- 让候选人能力验证更充分。
- 让最终评价更可追溯。
