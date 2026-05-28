"""简历文件文本提取"""
import logging

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import docx
except ImportError:
    docx = None


class PDFExtractor:
    @staticmethod
    def extract(file_path: str) -> str:
        if pdfplumber is None:
            logging.error("pdfplumber 未安装，请运行: pip install pdfplumber")
            return ""
        text_content = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)
            return "\n".join(text_content)
        except Exception as e:
            logging.error(f"PDF 解析失败: {e}")
            return ""


class DocxExtractor:
    @staticmethod
    def extract(file_path: str) -> str:
        if docx is None:
            logging.error("python-docx 未安装，请运行: pip install python-docx")
            return ""
        text_content = []
        try:
            d = docx.Document(file_path)
            for para in d.paragraphs:
                if para.text.strip():
                    text_content.append(para.text.strip())
            for table in d.tables:
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_data:
                        text_content.append(" | ".join(row_data))
            return "\n".join(text_content)
        except Exception as e:
            logging.error(f"Word 解析失败: {e}")
            return ""


class ImageExtractor:
    """图片 OCR 提取（需要 paddleocr，可选依赖）"""
    def __init__(self):
        try:
            from paddleocr import PaddleOCR
            logging.info("正在加载 PaddleOCR 模型...")
            self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        except ImportError:
            logging.warning("paddleocr 未安装，图片解析功能不可用")
            self.ocr = None

    def extract(self, file_path: str) -> str:
        if self.ocr is None:
            return ""
        text_content = []
        try:
            result = self.ocr.ocr(file_path, cls=True)
            for idx in range(len(result)):
                res = result[idx]
                if res is not None:
                    for line in res:
                        text_content.append(line[1][0])
            return "\n".join(text_content)
        except Exception as e:
            logging.error(f"图片 OCR 解析失败: {e}")
            return ""
