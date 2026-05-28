"""简历文本清洗"""
import re


class TextCleaner:
    @staticmethod
    def clean(raw_text: str) -> str:
        if not raw_text:
            return ""
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', raw_text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'([a-zA-Z]+)-\n([a-zA-Z]+)', r'\1\2', text)
        lines = [line.strip() for line in text.split('\n')]
        return "\n".join(lines)
