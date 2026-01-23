from fastapi import UploadFile
import io
import PyPDF2
from app.core.logging import logger


class FileService:
    async def parse_pdf(self, file: UploadFile) -> str:
        """
        Extract text from PDF file.
        """
        try:
            content = await file.read()
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"PDF 파싱 에러: {e}", exc_info=True)
            return f"Error extracting text from PDF: {str(e)}"

    async def parse_hwp(self, file: UploadFile) -> str:
        """
        Extract text from HWP file. (Placeholder)
        """
        return "HWP Parsing is not yet implemented. Please upload PDF."

    async def get_text_from_file(self, file: UploadFile) -> str:
        filename = file.filename.lower()
        if filename.endswith(".pdf"):
            return await self.parse_pdf(file)
        elif filename.endswith(".hwp"):
            return await self.parse_hwp(file)
        else:
            return "Unsupported file format. Please upload PDF or HWP."

file_service = FileService()
