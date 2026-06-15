"""简历解析完整流水线"""
import os
import logging
import time
import uuid
from typing import Optional

from app.services.resume.extractors import PDFExtractor, DocxExtractor, ImageExtractor
from app.services.resume.cleaner import TextCleaner
from app.services.resume.llm_agent import SemanticAnalyzerAgent
from app.services.resume.github_crawler import DigitalFootprintMiner
from app.storage.career_profile_store import list_career_profiles


class ResumePipelineEngine:
    def __init__(self):
        self.img_ext = ImageExtractor()
        self.pdf_ext = PDFExtractor(image_extractor=self.img_ext)
        self.docx_ext = DocxExtractor()
        self.cleaner = TextCleaner()
        self.llm_agent = SemanticAnalyzerAgent()
        self.miner = DigitalFootprintMiner()

    def run_pipeline(self, file_path: str, original_filename: Optional[str] = None) -> dict:
        started = time.time()
        ext = os.path.splitext(file_path)[1].lower()
        source_name = original_filename or os.path.basename(file_path)
        resume_id = f"RES_{uuid.uuid4().hex[:10].upper()}"
        raw_text = ""
        stages = []
        try:
            if ext == '.pdf':
                raw_text = self.pdf_ext.extract(file_path)
                stages.append({"name": "pdf_text_or_ocr", "status": "done"})
            elif ext in ['.docx', '.doc']:
                raw_text = self.docx_ext.extract(file_path)
                stages.append({"name": "word_text", "status": "done"})
            elif ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']:
                raw_text = self.img_ext.extract(file_path)
                stages.append({"name": "image_ocr", "status": "done"})
            else:
                return self._failed_result(resume_id, source_name, f"不支持的文件格式: {ext}", started)
        except Exception as e:
            logging.exception("简历文本抽取异常")
            return self._failed_result(resume_id, source_name, f"文本抽取失败: {e}", started)

        if not raw_text.strip():
            return self._failed_result(resume_id, source_name, "未能从文件中提取到有效文本", started)

        clean_text = self.cleaner.clean(raw_text)
        stages.append({"name": "clean_text", "status": "done", "chars": len(clean_text)})
        career_profiles = list_career_profiles()
        semantic_data = self.llm_agent.analyze(clean_text, career_profiles=career_profiles)
        stages.append({"name": "semantic_analysis", "status": "done"})
        footprint_data = self.miner.mine_data(clean_text)
        stages.append({"name": "digital_footprint", "status": footprint_data.get("status", "done")})

        return {
            "resume_id": resume_id,
            "source_filename": source_name,
            "status": "success",
            "parsed_data": {
                "name": semantic_data.get("name", ""),
                "contact": semantic_data.get("contact", {}),
                "claims": semantic_data.get("claims", []),
                "formatted_claims": semantic_data.get("formatted_claims", []),
                "objective_experiences": semantic_data.get("objective_experiences", []),
                "project_experiences": semantic_data.get("project_experiences", []),
                "multidimensional_profile": semantic_data.get("multidimensional_profile", {}),
                "growth_potential": semantic_data.get("growth_potential", {}),
                "suitable_roles": semantic_data.get("suitable_roles", []),
                "interview_questions": semantic_data.get("interview_questions", []),
                "digital_footprint": footprint_data
            },
            "blind_spots": semantic_data.get("blind_spots", []),
            "raw_text_preview": clean_text[:2000],
            "metadata": {
                "processing_seconds": round(time.time() - started, 3),
                "text_chars": len(clean_text),
                "stages": stages,
            },
        }

    def _failed_result(self, resume_id: str, source_name: str, error: str, started: float) -> dict:
        return {
            "resume_id": resume_id,
            "source_filename": source_name,
            "status": "failed",
            "error": error,
            "parsed_data": {
                "name": "",
                "contact": {},
                "claims": [],
                "formatted_claims": [],
                "objective_experiences": [],
                "project_experiences": [],
                "multidimensional_profile": {},
                "growth_potential": {},
                "suitable_roles": [],
                "interview_questions": [],
                "digital_footprint": {},
            },
            "blind_spots": [],
            "metadata": {"processing_seconds": round(time.time() - started, 3), "stages": []},
        }
