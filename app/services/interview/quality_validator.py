"""模块 E：判断质量验证框架。"""
from __future__ import annotations

from datetime import datetime
from typing import Any


class JudgmentQualityValidator:
    """对综合评估结果做证据链、稳定性、区分度三层验证。"""

    def validate(self, interview: dict, evaluation: dict, all_interviews: list[dict]) -> dict:
        evidence_chain = self._build_evidence_chain_report(evaluation)
        stability = self._build_stability_report(interview, evaluation, all_interviews)
        discrimination = self._build_discrimination_report(interview, evaluation, all_interviews)
        flags = self._build_manual_review_flags(evidence_chain, stability, discrimination)

        return {
            "version": "E-1",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "evidence_chain_health": self._summarize_evidence_health(evidence_chain),
                "stability_status": stability["status"],
                "discrimination_status": discrimination["status"],
                "needs_manual_review": bool(flags),
            },
            "evidence_chain_report": evidence_chain,
            "stability_report": stability,
            "discrimination_report": discrimination,
            "manual_review_flags": flags,
        }

    def _build_evidence_chain_report(self, evaluation: dict) -> dict:
        items = []
        for dim in evaluation.get("dimension_reports") or []:
            items.append(self._score_evidence_item(
                target_type="dimension",
                target_name=dim.get("dimension_name", "未命名维度"),
                signal_level=dim.get("signal_level", ""),
                evidence=dim.get("evidence") or [],
                blind_spot=dim.get("blind_spot", ""),
            ))
        for risk in evaluation.get("risks") or []:
            items.append(self._score_evidence_item(
                target_type="risk",
                target_name=risk.get("title", "未命名风险"),
                signal_level=risk.get("severity", ""),
                evidence=risk.get("evidence") or [],
                blind_spot=risk.get("blind_spot", ""),
            ))

        status_breakdown = {"证据充分": 0, "证据较弱": 0, "无依据": 0}
        for item in items:
            status_breakdown[item["status"]] += 1

        return {
            "status": self._aggregate_evidence_status(status_breakdown),
            "status_breakdown": status_breakdown,
            "items": items,
        }

    def _build_stability_report(self, interview: dict, evaluation: dict, all_interviews: list[dict]) -> dict:
        current_id = interview.get("interview_id")
        candidate_key = (
            interview.get("candidate", {}).get("candidate_ref")
            or interview.get("_candidate", {}).get("_id")
            or interview.get("candidate", {}).get("name")
        )
        comparable = [
            item for item in all_interviews
            if item.get("interview_id") != current_id
            and item.get("status") == "已完成"
            and item.get("evaluation")
            and (
                item.get("candidate", {}).get("candidate_ref")
                or item.get("_candidate", {}).get("_id")
                or item.get("candidate", {}).get("name")
            ) == candidate_key
        ]
        if not comparable:
            return {
                "status": "样本不足",
                "sample_size": 0,
                "consistency_rate": None,
                "comparable_interviews": [],
                "dimension_checks": [],
            }

        current_map = self._dimension_level_map(evaluation)
        checks = []
        consistent = 0
        total = 0
        for dimension_name, current_level in current_map.items():
            previous_levels = []
            previous_evidence_counts = []
            for item in comparable:
                prev_dim_map = self._dimension_level_map(item.get("evaluation") or {})
                prev_evidence_map = self._dimension_evidence_count_map(item.get("evaluation") or {})
                if dimension_name in prev_dim_map:
                    previous_levels.append(prev_dim_map[dimension_name])
                    previous_evidence_counts.append(prev_evidence_map.get(dimension_name, 0))
            if not previous_levels:
                continue
            total += 1
            normalized_previous = {self._normalize_level(level) for level in previous_levels}
            current_normalized = self._normalize_level(current_level)
            current_evidence = self._dimension_evidence_count_map(evaluation).get(dimension_name, 0)
            previous_average = round(sum(previous_evidence_counts) / max(len(previous_evidence_counts), 1), 2)

            if current_normalized in normalized_previous:
                status = "一致"
                explanation = "与历史同一候选人的核心判断基本一致。"
                consistent += 1
            elif current_evidence > previous_average:
                status = "合理修正"
                explanation = "本次判断与历史不同，但当前证据量更高，变化可以解释为信息增量带来的修正。"
            else:
                status = "存疑"
                explanation = "判断发生了变化，但当前没有看到明显更强的新证据，建议人工复核。"

            checks.append({
                "dimension_name": dimension_name,
                "current_signal": current_level,
                "previous_signals": previous_levels,
                "status": status,
                "explanation": explanation,
            })

        if total == 0:
            status = "样本不足"
            consistency_rate = None
        else:
            consistency_rate = round(consistent / total, 2)
            if any(item["status"] == "存疑" for item in checks):
                status = "需复核"
            elif consistency_rate >= 0.7:
                status = "稳定"
            else:
                status = "波动偏高"

        return {
            "status": status,
            "sample_size": len(comparable),
            "consistency_rate": consistency_rate,
            "comparable_interviews": [item.get("interview_id") for item in comparable],
            "dimension_checks": checks,
        }

    def _build_discrimination_report(self, interview: dict, evaluation: dict, all_interviews: list[dict]) -> dict:
        position_key = (
            interview.get("candidate", {}).get("profile_ref")
            or interview.get("_profile", {}).get("position", {}).get("title")
        )
        comparable = [
            item for item in all_interviews
            if item.get("status") == "已完成"
            and item.get("evaluation")
            and (
                item.get("candidate", {}).get("profile_ref")
                or item.get("_profile", {}).get("position", {}).get("title")
            ) == position_key
        ]
        if len(comparable) < 3:
            return {
                "status": "样本不足",
                "sample_size": len(comparable),
                "profile_ref": position_key or "未知岗位",
                "dimension_checks": [],
            }

        dimension_pool: dict[str, list[str]] = {}
        for item in comparable:
            for name, level in self._dimension_level_map(item.get("evaluation") or {}).items():
                dimension_pool.setdefault(name, []).append(level)

        checks = []
        effective_count = 0
        for name, levels in dimension_pool.items():
            normalized = [self._normalize_level(level) for level in levels]
            unique_levels = sorted(set(normalized))
            if len(unique_levels) >= 3:
                status = "有效区分"
                explanation = "同岗位候选人在该维度上出现了明显差异，可作为决策参考。"
                effective_count += 1
            elif len(unique_levels) == 2:
                status = "区分度偏低"
                explanation = "存在差异，但还不够稳定或不够拉开。"
            else:
                status = "失效"
                explanation = "该维度对几乎所有候选人给出了相同判断，说明区分力不足。"

            checks.append({
                "dimension_name": name,
                "status": status,
                "unique_levels": unique_levels,
                "compared_candidate_count": len(levels),
                "explanation": explanation,
            })

        if effective_count >= max(2, len(checks) // 3):
            status = "有效"
        elif effective_count == 0:
            status = "偏弱"
        else:
            status = "一般"

        return {
            "status": status,
            "sample_size": len(comparable),
            "profile_ref": position_key or "未知岗位",
            "dimension_checks": checks,
        }

    def _build_manual_review_flags(self, evidence_chain: dict, stability: dict, discrimination: dict) -> list[str]:
        flags = []
        unsupported = [item for item in evidence_chain.get("items") or [] if item["status"] == "无依据"]
        if unsupported:
            flags.append(f"有 {len(unsupported)} 条判断缺少直接证据支撑，不能直接用于决策。")
        weak = [item for item in evidence_chain.get("items") or [] if item["status"] == "证据较弱"]
        if weak:
            flags.append(f"有 {len(weak)} 条判断证据较弱，建议补追问或人工复核。")
        if stability.get("status") in {"需复核", "波动偏高"}:
            flags.append("同一候选人的跨次判断存在波动，需区分是新信息修正还是模型不稳定。")
        if discrimination.get("status") in {"偏弱", "一般"}:
            flags.append("当前岗位样本上的区分度还不够强，部分维度可能没有真正拉开候选人差异。")
        return flags

    def _score_evidence_item(
        self,
        target_type: str,
        target_name: str,
        signal_level: str,
        evidence: list[dict],
        blind_spot: str,
    ) -> dict:
        evidence_count = len(evidence)
        avg_quote_len = 0
        if evidence_count:
            avg_quote_len = round(sum(len((item.get("quote") or "").strip()) for item in evidence) / evidence_count, 2)

        if evidence_count >= 2 and avg_quote_len >= 25:
            status = "证据充分"
            reason = "存在多条原始证据，且证据片段具有一定信息密度。"
        elif evidence_count >= 1:
            status = "证据较弱"
            reason = "有证据，但证据数量或信息密度仍不足以支撑高置信判断。"
        else:
            status = "无依据"
            reason = blind_spot or "该判断没有绑定到可追溯的原始证据。"

        return {
            "target_type": target_type,
            "target_name": target_name,
            "signal_level": signal_level,
            "status": status,
            "reason": reason,
            "evidence_count": evidence_count,
            "evidence_refs": [
                {
                    "turn_index": item.get("turn_index"),
                    "question_id": item.get("question_id"),
                }
                for item in evidence[:5]
            ],
        }

    def _aggregate_evidence_status(self, breakdown: dict[str, int]) -> str:
        if breakdown["无依据"] > 0:
            return "薄弱"
        if breakdown["证据较弱"] > breakdown["证据充分"]:
            return "一般"
        return "健康"

    def _summarize_evidence_health(self, evidence_chain: dict) -> str:
        status = evidence_chain.get("status")
        if status == "健康":
            return "健康"
        if status == "一般":
            return "一般"
        return "薄弱"

    def _dimension_level_map(self, evaluation: dict) -> dict[str, str]:
        return {
            item.get("dimension_name", "未命名维度"): item.get("signal_level", "待验证")
            for item in evaluation.get("dimension_reports") or []
            if item.get("dimension_name")
        }

    def _dimension_evidence_count_map(self, evaluation: dict) -> dict[str, int]:
        return {
            item.get("dimension_name", "未命名维度"): len(item.get("evidence") or [])
            for item in evaluation.get("dimension_reports") or []
            if item.get("dimension_name")
        }

    def _normalize_level(self, value: Any) -> str:
        text = str(value or "")
        if "风险" in text:
            return "风险"
        if "强" in text:
            return "强"
        if "有信号" in text:
            return "中"
        if "待验证" in text or "不足" in text:
            return "待验证"
        return text or "待验证"

