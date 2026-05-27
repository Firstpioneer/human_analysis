"""简历文件文本提取"""
import io
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
    def __init__(self, image_extractor=None):
        self.image_extractor = image_extractor

    @staticmethod
    def _extract_with_pdfplumber(file_path: str) -> str:
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

    def _extract_with_ocr(self, file_path: str) -> str:
        if not self.image_extractor or not self.image_extractor.available:
            return ""
        try:
            import fitz
            from PIL import Image
        except ImportError:
            logging.warning("PyMuPDF/Pillow 未安装，无法对图片型 PDF 执行 OCR")
            return ""

        text_content = []
        try:
            doc = fitz.open(file_path)
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                page_text = self.image_extractor.extract_image(image)
                if page_text:
                    text_content.append(page_text)
            return "\n".join(text_content)
        except Exception as e:
            logging.error(f"PDF OCR 解析失败: {e}")
            return ""

    def extract(self, file_path: str) -> str:
        text = self._extract_with_pdfplumber(file_path)
        # 图片型 PDF 或复杂排版 PDF 常只有很少文本，此时尝试 OCR 回退。
        if len(text.strip()) < 80:
            ocr_text = self._extract_with_ocr(file_path)
            if len(ocr_text.strip()) > len(text.strip()):
                return ocr_text
        return text


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
            logging.warning(f"python-docx 解析失败，尝试 mammoth: {e}")
            try:
                import mammoth
                with open(file_path, "rb") as f:
                    result = mammoth.extract_raw_text(f)
                return result.value or ""
            except Exception as mammoth_error:
                logging.error(f"Word 解析失败: {mammoth_error}")
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

    @property
    def available(self) -> bool:
        return self.ocr is not None

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

    def extract_image(self, image) -> str:
        if self.ocr is None:
            return ""
        text_content = []
        try:
            try:
                import numpy as np
                ocr_input = np.array(image)
            except ImportError:
                ocr_input = image
            result = self.ocr.ocr(ocr_input, cls=True)
            for res in result:
                if res is not None:
                    for line in res:
                        text_content.append(line[1][0])
            return "\n".join(text_content)
        except Exception as e:
            logging.error(f"内存图片 OCR 解析失败: {e}")
            return ""
