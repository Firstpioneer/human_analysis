"""简历解析完整流水线"""
import os
import logging
from app.services.resume.extractors import PDFExtractor, DocxExtractor, ImageExtractor
from app.services.resume.cleaner import TextCleaner
from app.services.resume.llm_agent import SemanticAnalyzerAgent
from app.services.resume.github_crawler import DigitalFootprintMiner


class ResumePipelineEngine:
    def __init__(self):
        self.pdf_ext = PDFExtractor()
        self.docx_ext = DocxExtractor()
        self.img_ext = ImageExtractor()
        self.cleaner = TextCleaner()
        self.llm_agent = SemanticAnalyzerAgent()
        self.miner = DigitalFootprintMiner()

    def run_pipeline(self, file_path: str) -> dict:
        ext = os.path.splitext(file_path)[1].lower()
        raw_text = ""
        if ext == '.pdf':
            raw_text = self.pdf_ext.extract(file_path)
        elif ext in ['.docx', '.doc']:
            raw_text = self.docx_ext.extract(file_path)
        elif ext in ['.png', '.jpg', '.jpeg']:
            raw_text = self.img_ext.extract(file_path)

        if not raw_text.strip():
            return {
                "resume_id": os.path.basename(file_path),
                "status": "failed",
                "error": "未能从文件中提取到有效文本",
                "parsed_data": {"claims": [], "objective_experiences": [], "digital_footprint": {}},
                "blind_spots": []
            }

        clean_text = self.cleaner.clean(raw_text)
        semantic_data = self.llm_agent.analyze(clean_text)
        footprint_data = self.miner.mine_data(clean_text)

        return {
            "resume_id": os.path.basename(file_path),
            "status": "success",
            "parsed_data": {
                "claims": semantic_data.get("claims", []),
                "objective_experiences": semantic_data.get("objective_experiences", []),
                "digital_footprint": footprint_data
            },
            "blind_spots": semantic_data.get("blind_spots", [])
        }
