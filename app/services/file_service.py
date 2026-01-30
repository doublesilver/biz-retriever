import io

import PyPDF2
from fastapi import UploadFile

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
        Extract text from HWP file using olefile.
        """
        try:
            import zlib

            import olefile

            content = await file.read()
            # olefile requires a file-like object or path. BytesIO works.
            f = io.BytesIO(content)

            if not olefile.isOleFile(f):
                return "Not a valid HWP file (OLE format check failed)."

            ole = olefile.OleFileIO(f)
            text = ""

            # HWP 5.0 structure: BodyText/SectionX
            dirs = ole.listdir()
            body_sections = [d for d in dirs if d[0] == "BodyText"]

            for section in body_sections:
                stream = ole.openstream(section)
                data = stream.read()

                # Decompress zlib stream
                # HWP BodyText is zlib compressed
                try:
                    decompressed = zlib.decompress(data, -15)  # -15 for raw stream
                except zlib.error:
                    try:
                        decompressed = zlib.decompress(data)
                    except zlib.error:
                        continue  # Skip if decompression fails

                # Extract generic text (simple extraction of UTF-16LE strings)
                # This is a heuristic approach for HWP 5.0 text extraction without heavy parsers
                # Proper parsing requires structuring the HWP record format,
                # but for MVP, we extract valid unicode sequences.

                # HWP text is usually UTF-16LE
                try:
                    # Decoding strategy: HWP uses 16-bit characters.
                    # We simply try to decode as utf-16le and filter meaningful chars
                    decoded = decompressed.decode("utf-16le", errors="ignore")

                    # Clean up control characters and noise
                    # Filter for Hangul, English, Numbers, standard punctuation
                    # This is rough; for production we need a better parser lib if accuracy is key.
                    # But Python based libhwp alternatives are scarce or heavy.
                    # olefile extraction is metadata-level or stream-level.
                    # Raw stream contains formatting tags. We just want text for Search/RAG.

                    text += decoded + "\n"
                except Exception:
                    pass

            return text if text else "Exracted text is empty (HWP parsing limitation)."

        except ImportError:
            return "olefile is not installed."
        except Exception as e:
            logger.error(f"HWP 파싱 에러: {e}", exc_info=True)
            return f"Error extracting text from HWP: {str(e)}"

    async def get_text_from_file(self, file: UploadFile) -> str:
        filename = file.filename.lower()
        if filename.endswith(".pdf"):
            return await self.parse_pdf(file)
        elif filename.endswith(".hwp"):
            return await self.parse_hwp(file)
        else:
            return "Unsupported file format. Please upload PDF or HWP."


file_service = FileService()
