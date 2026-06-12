"""面试实时推理引擎（增强版）

每轮候选人回答后：
- 分析证据、更新维度验证状态
- 检查跨轮次一致性
- 评估回答质量（逻辑性/具体性/反思性/主动性）
- 时间感知的动态优先级
- 决定下一步动作
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from .llm_service import get_llm_service

logger = logging.getLogger(__name__)


@dataclass
class DimensionState:
    """单个验证维度的状态"""
    dimension_id: str
    name: str
    category: str = "技术"
    priority: str = "nice_to_have"  # must_have / nice_to_have / risk_check
    criteria: str = ""
    success_signals: list = field(default_factory=list)
    risk_signals: list = field(default_factory=list)
    probing_strategies: list = field(default_factory=list)

    # 动态状态
    status: str = "not_started"  # not_started / partial / verified / risk
    confidence: float = 0.0
    evidence_count: int = 0
    evidence_summary: str = ""
    risk_flags: list = field(default_factory=list)
    last_updated_turn: int = 0


@dataclass
class AnswerQuality:
    """回答质量评估"""
    logic_score: float = 0.0       # 逻辑性：因果链是否清晰
    specificity_score: float = 0.0 # 具体性：是否有细节/数据
    reflection_score: float = 0.0  # 反思性：是否能说不足/改进
    initiative_score: float = 0.0  # 主动性：被动回答 vs 主动展开
    overall_score: float = 0.0
    quality_flags: list = field(default_factory=list)


@dataclass
class ClaimedFact:
    """候选人声称的事实"""
    turn: int
    content: str
    dimension_id: str = ""
    fact_type: str = ""  # role / achievement / tech / timeline


@dataclass
class ReasoningResult:
    """单次推理结果"""
    turn: int
    reasoning: str
    action: str  # deepen / advance / probe_risk / verify_authenticity / skip / wrap_up
    target_dimension: str = ""
    next_question_hint: str = ""
    evidence_extracted: str = ""
    dimension_updates: dict = field(default_factory=dict)
    answer_quality: Optional[AnswerQuality] = None
    consistency_flags: list = field(default_factory=list)
    needs_authenticity_check: bool = False


class InterviewReasoner:
    """面试实时推理引擎"""

    def __init__(self, use_llm: bool = True):
        self._use_llm = use_llm
        self._dimensions: dict[str, DimensionState] = {}
        self._reasoning_log: list[dict] = []
        self._claimed_facts: list[ClaimedFact] = []
        self._turn_counter: int = 0
        self._profile: Optional[dict] = None

    def _get_llm(self):
        if not self._use_llm:
            return None
        svc = get_llm_service()
        return svc if svc.is_available else None

    def initialize(self, plan: dict, profile: dict):
        """从验证计划初始化维度状态"""
        self._profile = profile
        self._dimensions = {}
        self._reasoning_log = []
        self._claimed_facts = []
        self._turn_counter = 0

        for dim in plan.get("verification_dimensions", []):
            dim_id = dim.get("dimension_id", "")
            if not dim_id:
                continue
            self._dimensions[dim_id] = DimensionState(
                dimension_id=dim_id,
                name=dim.get("name", ""),
                category=dim.get("category", "技术"),
                priority=dim.get("priority", "nice_to_have"),
                criteria=dim.get("criteria", ""),
                success_signals=dim.get("success_signals", []),
                risk_signals=dim.get("risk_signals", []),
                probing_strategies=dim.get("probing_strategies", []),
            )

        logger.info("推理引擎初始化完成: %d 个验证维度", len(self._dimensions))

    def analyze_answer(self, question_text: str, answer_text: str,
                       question_category: str = "", linked_dimension: str = "",
                       elapsed_minutes: float = 0, total_minutes: float = 45,
                       dialogue_history: list = None) -> ReasoningResult:
        """分析候选人回答，更新维度状态，决定下一步"""
        self._turn_counter += 1

        # P3: 规则层回答质量评估
        quality = self._assess_answer_quality(answer_text)

        # P1: 规则层一致性检查
        consistency_flags = self._check_consistency(answer_text, linked_dimension)

        # 尝试用 LLM 做深度分析
        llm_result = self._analyze_with_llm(
            question_text, answer_text, question_category,
            linked_dimension, elapsed_minutes, total_minutes,
            dialogue_history or [], quality, consistency_flags,
        )

        if llm_result:
            return llm_result

        # LLM 不可用时，用增强规则兜底
        return self._analyze_with_rules(
            question_text, answer_text, linked_dimension,
            elapsed_minutes, total_minutes, quality, consistency_flags,
        )

    def _assess_answer_quality(self, answer_text: str) -> AnswerQuality:
        """P3: 规则层回答质量评估"""
        text = answer_text.strip()
        length = len(text)
        quality = AnswerQuality()

        # 逻辑性：检查因果连接词
        logic_keywords = ["因为", "所以", "导致", "从而", "于是", "因此", "由于", "结果是",
                          "首先", "然后", "最后", "第一步", "接下来", "具体来说"]
        logic_hits = sum(1 for kw in logic_keywords if kw in text)
        quality.logic_score = min(1.0, logic_hits * 0.25)

        # 具体性：检查细节指标
        detail_keywords = ["比如", "例如", "具体", "数据", "指标", "百分比", "%",
                           "万", "亿", "毫秒", "秒", "倍", "个", "次",
                           "版本", "配置", "参数", "接口", "表", "字段"]
        detail_hits = sum(1 for kw in detail_keywords if kw in text)
        quality.specificity_score = min(1.0, detail_hits * 0.2 + (0.2 if length > 100 else 0))

        # 反思性：检查自我反思
        reflection_keywords = ["不足", "改进", "教训", "反思", "如果重来", "下次",
                                "遗憾", "遗憾的是", "当时应该", "后来发现", "问题在于",
                                "缺点", "短板", "不够", "欠缺"]
        reflection_hits = sum(1 for kw in reflection_keywords if kw in text)
        quality.reflection_score = min(1.0, reflection_hits * 0.35)

        # 主动性：回答长度和展开程度
        if length < 30:
            quality.initiative_score = 0.0
        elif length < 80:
            quality.initiative_score = 0.3
        elif length < 200:
            quality.initiative_score = 0.6
        else:
            quality.initiative_score = 0.9

        # 综合分
        quality.overall_score = (
            quality.logic_score * 0.3 +
            quality.specificity_score * 0.3 +
            quality.reflection_score * 0.2 +
            quality.initiative_score * 0.2
        )

        # 质量标记
        if quality.specificity_score < 0.2 and length > 30:
            quality.quality_flags.append("缺少具体细节")
        if quality.logic_score < 0.15 and length > 50:
            quality.quality_flags.append("逻辑链不清晰")
        if quality.reflection_score >= 0.35:
            quality.quality_flags.append("有自我反思")

        return quality

    def _check_consistency(self, answer_text: str, linked_dimension: str) -> list[str]:
        """P1: 跨轮次一致性检查"""
        flags = []
        text = answer_text.strip()

        # 提取当前回答中的关键声称
        self._extract_claims(text, linked_dimension)

        # 与历史声称对比
        for fact in self._claimed_facts[-20:]:  # 只检查最近 20 条
            if fact.turn == self._turn_counter:
                continue
            contradiction = self._detect_contradiction(fact.content, text)
            if contradiction:
                flags.append(f"[回合{fact.turn}] \"{fact.content[:30]}\" vs 当前回答: {contradiction}")

        return flags

    def _extract_claims(self, text: str, dimension_id: str):
        """从回答中提取关键声称"""
        # 提取角色声称
        role_patterns = ["我负责", "我主导", "我设计", "我开发", "我实现", "我优化",
                         "我带领", "我管理", "我架构", "我搭建"]
        for pattern in role_patterns:
            if pattern in text:
                idx = text.index(pattern)
                claim = text[max(0, idx):min(len(text), idx + 60)]
                self._claimed_facts.append(ClaimedFact(
                    turn=self._turn_counter, content=claim.strip(),
                    dimension_id=dimension_id, fact_type="role"
                ))
                break

        # 提取成果声称
        achievement_patterns = ["提升了", "降低了", "优化了", "增长了", "减少了",
                                "提高了", "节省了", "从.*到"]
        for pattern in achievement_patterns:
            if pattern in text:
                idx = text.index(pattern)
                claim = text[max(0, idx):min(len(text), idx + 60)]
                self._claimed_facts.append(ClaimedFact(
                    turn=self._turn_counter, content=claim.strip(),
                    dimension_id=dimension_id, fact_type="achievement"
                ))
                break

        # 提取技术声称
        tech_patterns = ["使用了", "采用了", "选用了", "基于", "搭建了", "引入了"]
        for pattern in tech_patterns:
            if pattern in text:
                idx = text.index(pattern)
                claim = text[max(0, idx):min(len(text), idx + 60)]
                self._claimed_facts.append(ClaimedFact(
                    turn=self._turn_counter, content=claim.strip(),
                    dimension_id=dimension_id, fact_type="tech"
                ))
                break

    def _detect_contradiction(self, old_claim: str, new_text: str) -> str:
        """检测两段文本之间的矛盾"""
        # 独立 vs 团队
        independent = ["独立", "自己", "一个人", "我负责", "我主导"]
        team = ["团队", "一起", "大家", "协作", "讨论", "共同"]

        old_independent = any(kw in old_claim for kw in independent)
        new_team = any(kw in new_text for kw in team)
        if old_independent and new_team:
            return "之前声称独立负责，当前提到团队协作"

        old_team = any(kw in old_claim for kw in team)
        new_independent = any(kw in new_text for kw in independent)
        if old_team and new_independent:
            return "之前提到团队协作，当前声称独立负责"

        # 数量/程度矛盾
        import re
        old_numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(%|倍|万|亿|个|台|次|秒|毫秒)', old_claim)
        new_numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(%|倍|万|亿|个|台|次|秒|毫秒)', new_text)
        if old_numbers and new_numbers:
            for old_val, old_unit in old_numbers:
                for new_val, new_unit in new_numbers:
                    if old_unit == new_unit:
                        try:
                            diff = abs(float(old_val) - float(new_val)) / max(float(old_val), 1)
                            if diff > 0.5:
                                return f"数据不一致: 之前说{old_val}{old_unit}，现在说{new_val}{new_unit}"
                        except ValueError:
                            pass

        return ""

    def _analyze_with_llm(self, question_text, answer_text, question_category,
                          linked_dimension, elapsed_minutes, total_minutes,
                          dialogue_history, quality, consistency_flags) -> Optional[ReasoningResult]:
        llm = self._get_llm()
        if not llm:
            return None

        dim_status_text = self._build_dimension_status_text()
        claimed_facts_text = self._build_claimed_facts_text()
        quality_text = self._build_quality_text(quality)
        consistency_text = "\n".join(f"- {f}" for f in consistency_flags) if consistency_flags else "无矛盾"

        history_text = ""
        if dialogue_history:
            recent = dialogue_history[-6:]
            history_text = "\n".join(
                f"[{d.get('speaker', '?')}] {d.get('text', '')[:80]}"
                for d in recent
            )

        remaining_minutes = max(0, total_minutes - elapsed_minutes)

        system_prompt = """你是一位资深面试官的实时推理助手。你需要分析候选人的最新回答，判断它对各个验证维度的贡献，并决定面试的下一步动作。

你必须严格按以下 JSON 格式返回：

{
  "evidence_extracted": "从回答中提取的关键证据摘要（一句话）",
  "dimension_updates": {
    "D001": {
      "new_status": "partial|verified|risk",
      "confidence_delta": 0.0到1.0之间的增量,
      "evidence_addition": "新发现的证据",
      "risk_flag": ""
    }
  },
  "action": "deepen|advance|probe_risk|verify_authenticity|skip|wrap_up",
  "target_dimension": "D001",
  "reasoning": "为什么选择这个动作（一句话）",
  "next_question_hint": "下一个问题应该问什么方向（一句话）",
  "needs_authenticity_check": true或false,
  "consistency_flags": ["发现的矛盾，如有"]
}

动作选择规则：
- deepen：当前维度证据不足，需要继续追问
- advance：当前维度已验证，跳到下一个未覆盖维度
- probe_risk：发现风险信号，需要深入探查
- verify_authenticity：回答匹配了 success_signals 但缺乏具体细节，需要验证真实性
- skip：剩余时间不足，跳过低优先级维度
- wrap_up：所有 must_have 维度已覆盖，或时间即将用完

判断标准：
- 回答中包含具体技术细节、实际数据、明确的因果关系 → 正面证据
- 回答模糊、回避细节、只说结论不说过程 → 风险信号
- 回答中提到"不知道"、"没做过"、"不太清楚" → 明确风险
- 回答过于简短（少于 30 字）且无实质内容 → 证据不足
- 回答听起来太完美/太模板化，缺乏个人经历细节 → 需要验证真实性
- 与之前声称的事实矛盾 → 标记一致性风险

时间感知规则：
- 剩余 > 15 分钟：可以深挖、追问真实性
- 剩余 8-15 分钟：优先覆盖 must_have 维度
- 剩余 < 8 分钟：只覆盖 must_have，跳过 nice_to_have
- 剩余 < 3 分钟：直接收尾"""

        user_prompt = f"""【当前维度状态】
{dim_status_text}

【候选人已声称的关键事实】
{claimed_facts_text or '（暂无）'}

【回答质量评估】
{quality_text}

【跨轮次一致性检查】
{consistency_text}

【最新问答】
面试官问：{question_text}
候选人答：{answer_text}
问题类别：{question_category}
关联维度：{linked_dimension or '未指定'}

【时间进度】
已用 {elapsed_minutes:.1f} 分钟，剩余 {remaining_minutes:.1f} 分钟

【最近对话】
{history_text or '（无）'}

请分析这个回答并决定下一步。"""

        try:
            result = llm.chat_json(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=1024,
            )
            if not result or "action" not in result:
                return None

            dim_updates = result.get("dimension_updates", {})
            if isinstance(dim_updates, dict):
                for dim_id, update in dim_updates.items():
                    if dim_id in self._dimensions and isinstance(update, dict):
                        self._apply_dimension_update(dim_id, update)

            # 合并 LLM 发现的一致性问题
            llm_flags = result.get("consistency_flags", [])
            all_flags = consistency_flags + (llm_flags if isinstance(llm_flags, list) else [])

            reasoning_result = ReasoningResult(
                turn=self._turn_counter,
                reasoning=result.get("reasoning", ""),
                action=result.get("action", "advance"),
                target_dimension=result.get("target_dimension", ""),
                next_question_hint=result.get("next_question_hint", ""),
                evidence_extracted=result.get("evidence_extracted", ""),
                dimension_updates=dim_updates if isinstance(dim_updates, dict) else {},
                answer_quality=quality,
                consistency_flags=all_flags,
                needs_authenticity_check=result.get("needs_authenticity_check", False),
            )

            self._reasoning_log.append(asdict(reasoning_result))
            logger.info("推理完成: turn=%d action=%s target=%s quality=%.2f consistency=%d",
                        self._turn_counter, reasoning_result.action,
                        reasoning_result.target_dimension, quality.overall_score, len(all_flags))
            return reasoning_result

        except Exception as e:
            logger.warning("LLM 推理失败: %s", e)
            return None

    def _analyze_with_rules(self, question_text, answer_text,
                            linked_dimension, elapsed_minutes, total_minutes,
                            quality, consistency_flags) -> ReasoningResult:
        """增强规则兜底"""
        answer_len = len(answer_text.strip())
        remaining = max(0, total_minutes - elapsed_minutes)

        # 更新关联维度
        if linked_dimension and linked_dimension in self._dimensions:
            dim = self._dimensions[linked_dimension]
            dim.evidence_count += 1
            dim.last_updated_turn = self._turn_counter

            # P3: 用质量分数调整置信度增量
            base_delta = 0.1 if answer_len < 20 else (0.2 if answer_len < 80 else 0.3)
            quality_multiplier = 0.5 + quality.overall_score  # 0.5 ~ 1.5
            delta = base_delta * quality_multiplier

            if answer_len < 20:
                dim.status = "partial"
            elif quality.overall_score >= 0.5 and answer_len >= 80:
                dim.status = "verified"
            else:
                dim.status = "partial"
            dim.confidence = min(1.0, max(0.0, dim.confidence + delta))

            # P1: 一致性风险
            if consistency_flags:
                dim.risk_flags.extend(consistency_flags[:2])
                dim.status = "risk"

        # P2: 时间感知决策
        action = "advance"
        target = ""
        hint = ""
        reasoning = ""

        uncovered_must = [
            d for d in self._dimensions.values()
            if d.priority == "must_have" and d.status in ("not_started", "partial")
        ]
        current_dim = self._dimensions.get(linked_dimension) if linked_dimension else None

        # P0: 真实性验证检查
        needs_auth = False
        if (current_dim and current_dim.status == "verified" and
                quality.specificity_score < 0.3 and answer_len > 50):
            needs_auth = True
            action = "verify_authenticity"
            target = linked_dimension
            hint = "回答匹配了成功信号但缺乏细节，需要验证真实性"
            reasoning = "回答听起来完整但缺少具体细节，需要追问验证"

        if not needs_auth:
            if remaining <= 3:
                action = "wrap_up"
                reasoning = "剩余时间不足，准备收尾"
            elif remaining <= 8 and uncovered_must:
                action = "skip"
                target = uncovered_must[0].dimension_id
                reasoning = f"时间紧张，跳到必验维度 {uncovered_must[0].name}"
            elif consistency_flags:
                action = "probe_risk"
                target = linked_dimension
                hint = "回答与之前声称存在矛盾，需要澄清"
                reasoning = f"发现一致性问题: {consistency_flags[0]}"
            elif quality.overall_score < 0.25 and answer_len > 20:
                action = "deepen"
                target = linked_dimension
                hint = "回答质量较低，需要追问细节"
                reasoning = "回答缺乏逻辑性或具体性，需要深挖"
            elif answer_len < 20 and linked_dimension:
                action = "deepen"
                target = linked_dimension
                hint = "请候选人展开说明"
                reasoning = "回答过于简短，需要追问"
            elif uncovered_must:
                action = "advance"
                target = uncovered_must[0].dimension_id
                reasoning = f"当前维度已覆盖，进入下一个必验维度 {uncovered_must[0].name}"
            else:
                uncovered_nice = [
                    d for d in self._dimensions.values()
                    if d.priority == "nice_to_have" and d.status == "not_started"
                ]
                if uncovered_nice and remaining > 5:
                    action = "advance"
                    target = uncovered_nice[0].dimension_id
                    reasoning = f"必验维度已覆盖，进入加分维度 {uncovered_nice[0].name}"
                else:
                    action = "wrap_up"
                    reasoning = "核心维度已覆盖，准备收尾"

        result = ReasoningResult(
            turn=self._turn_counter,
            reasoning=reasoning,
            action=action,
            target_dimension=target,
            next_question_hint=hint,
            evidence_extracted=answer_text[:100] if answer_len > 10 else "",
            answer_quality=quality,
            consistency_flags=consistency_flags,
            needs_authenticity_check=needs_auth,
        )

        self._reasoning_log.append(asdict(result))
        return result

    def _apply_dimension_update(self, dim_id: str, update: dict):
        """应用 LLM 返回的维度更新"""
        dim = self._dimensions.get(dim_id)
        if not dim:
            return

        new_status = update.get("new_status", "")
        if new_status in ("partial", "verified", "risk"):
            dim.status = new_status

        confidence_delta = update.get("confidence_delta", 0)
        if isinstance(confidence_delta, (int, float)):
            dim.confidence = min(1.0, max(0.0, dim.confidence + confidence_delta))

        evidence_addition = update.get("evidence_addition", "")
        if evidence_addition:
            dim.evidence_count += 1
            if dim.evidence_summary:
                dim.evidence_summary += "；" + evidence_addition
            else:
                dim.evidence_summary = evidence_addition

        risk_flag = update.get("risk_flag", "")
        if risk_flag and risk_flag not in dim.risk_flags:
            dim.risk_flags.append(risk_flag)

        dim.last_updated_turn = self._turn_counter

    def _build_dimension_status_text(self) -> str:
        lines = []
        for dim in self._dimensions.values():
            status_icon = {
                "not_started": "⬜", "partial": "🟡", "verified": "✅", "risk": "🔴",
            }.get(dim.status, "⬜")
            lines.append(
                f"{status_icon} [{dim.dimension_id}] {dim.name} "
                f"({dim.priority}) — {dim.status}, 置信度{dim.confidence:.1f}, "
                f"证据{dim.evidence_count}条"
                f"{'⚠️ ' + ', '.join(dim.risk_flags) if dim.risk_flags else ''}"
            )
        return "\n".join(lines) if lines else "（无维度）"

    def _build_claimed_facts_text(self) -> str:
        if not self._claimed_facts:
            return ""
        lines = []
        for fact in self._claimed_facts[-10:]:
            lines.append(f"[回合{fact.turn}] ({fact.type if hasattr(fact, 'type') else fact.fact_type}) {fact.content}")
        return "\n".join(lines)

    def _build_quality_text(self, quality: AnswerQuality) -> str:
        lines = [
            f"逻辑性: {quality.logic_score:.1f}/1.0",
            f"具体性: {quality.specificity_score:.1f}/1.0",
            f"反思性: {quality.reflection_score:.1f}/1.0",
            f"主动性: {quality.initiative_score:.1f}/1.0",
            f"综合: {quality.overall_score:.1f}/1.0",
        ]
        if quality.quality_flags:
            lines.append("标记: " + ", ".join(quality.quality_flags))
        return "\n".join(lines)

    def get_dimension_states(self) -> dict:
        return {dim_id: asdict(dim) for dim_id, dim in self._dimensions.items()}

    def get_reasoning_log(self) -> list[dict]:
        return list(self._reasoning_log)

    def get_claimed_facts(self) -> list[dict]:
        return [asdict(f) for f in self._claimed_facts]

    def get_uncovered_dimensions(self) -> list[DimensionState]:
        return [
            d for d in self._dimensions.values()
            if d.status in ("not_started", "partial") and d.priority == "must_have"
        ]

    def get_risk_dimensions(self) -> list[DimensionState]:
        return [
            d for d in self._dimensions.values()
            if d.status == "risk" or d.risk_flags
        ]

    def should_continue(self, elapsed_minutes: float, total_minutes: float) -> bool:
        remaining = total_minutes - elapsed_minutes
        if remaining <= 2:
            return False
        uncovered = self.get_uncovered_dimensions()
        if not uncovered and remaining <= 5:
            return False
        return True
