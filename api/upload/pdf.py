"""
POST /api/upload/pdf
사업자등록증 PDF 업로드 + Gemini AI 자동 추출
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import asyncio
import io
import cgi

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.utils import send_json, send_error, handle_cors_preflight
from lib.auth import require_auth
from lib.db import get_db
from app.services.profile_service import profile_service
from app.core.logging import logger

# File size limit: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_POST(self):
        """PDF 업로드 및 Gemini AI 자동 추출"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. Content-Type 검증
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                send_error(self, 400, "Content-Type must be multipart/form-data")
                return
            
            # 3. Content-Length 검증 (10MB 제한)
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > MAX_FILE_SIZE:
                send_error(self, 413, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")
                return
            
            # 4. 파일 파싱
            try:
                # Parse multipart/form-data
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={
                        'REQUEST_METHOD': 'POST',
                        'CONTENT_TYPE': content_type,
                    }
                )
                
                # Get file field
                if 'file' not in form:
                    send_error(self, 400, "Missing 'file' field in form data")
                    return
                
                file_item = form['file']
                if not file_item.file:
                    send_error(self, 400, "No file uploaded")
                    return
                
                # Read file content
                file_content = file_item.file.read()
                
                # Validate file size again (in case Content-Length was wrong)
                if len(file_content) > MAX_FILE_SIZE:
                    send_error(self, 413, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")
                    return
                
                # Validate PDF format (check magic bytes)
                if not file_content.startswith(b'%PDF'):
                    send_error(self, 400, "Invalid file format. Only PDF files are allowed")
                    return
                
            except Exception as e:
                logger.error(f"File parsing error: {e}", exc_info=True)
                send_error(self, 400, f"Failed to parse file: {str(e)}")
                return
            
            # 5. 비동기 처리
            result = asyncio.run(self.process_pdf(user_payload, file_content))
            
            # 6. 응답
            send_json(self, 200, result)
            
        except Exception as e:
            logger.error(f"PDF upload error: {e}", exc_info=True)
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def process_pdf(self, user_payload: dict, file_content: bytes):
        """PDF 텍스트 추출 + Gemini AI 분석 + 프로필 업데이트"""
        user_id = user_payload.get("user_id")
        
        # 1. PDF 텍스트 추출 (pymupdf)
        try:
            import fitz  # pymupdf
            
            # Open PDF from bytes
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            
            # Check if encrypted
            if pdf_document.is_encrypted:
                pdf_document.close()
                raise ValueError("Password-protected PDFs are not supported")
            
            # Extract text from all pages
            extracted_text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                extracted_text += page.get_text()
            
            pdf_document.close()
            
            # Clean extracted text (remove extra whitespace)
            extracted_text = " ".join(extracted_text.split())
            
            if not extracted_text.strip():
                raise ValueError("No text found in PDF. The document may be image-based or empty")
            
        except ImportError:
            raise ValueError("pymupdf (fitz) is not installed. Cannot extract PDF text")
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}", exc_info=True)
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
        
        # 2. Gemini AI 분석 (사업자등록증 정보 추출)
        try:
            async for db in get_db():
                # Call Gemini AI via profile_service
                # Note: parse_business_certificate expects image bytes, but we'll use text extraction
                # For PDF, we'll create a custom prompt with extracted text
                
                from app.services.rag_service import rag_service
                
                prompt = f"""다음은 사업자등록증에서 추출한 텍스트입니다. 
다음 정보를 JSON 형식으로 추출하세요:

추출된 텍스트:
{extracted_text[:2000]}

필수 추출 항목:
- company_name: 상호 또는 법인명
- brn: 사업자등록번호 (숫자만, 하이픈 제거)
- representative: 대표자 성명
- address: 사업장 주소 (전체 주소)

JSON 형식으로만 응답하세요. 예시:
{{
  "company_name": "주식회사 예시",
  "brn": "1234567890",
  "representative": "홍길동",
  "address": "서울특별시 강남구 테헤란로 123"
}}
"""
                
                # Call Gemini AI
                ai_result = await rag_service.analyze_bid(prompt)
                
                # Extract structured data from AI response
                # The AI should return summary with JSON-like structure
                # We'll parse the summary field
                import json
                import re
                
                summary = ai_result.get("summary", "")
                
                # Try to extract JSON from summary
                json_match = re.search(r'\{[^}]+\}', summary)
                if json_match:
                    extracted_data = json.loads(json_match.group(0))
                else:
                    # Fallback: use keywords to extract data
                    extracted_data = {
                        "company_name": None,
                        "brn": None,
                        "representative": None,
                        "address": None,
                    }
                    
                    # Try to extract from keywords
                    keywords = ai_result.get("keywords", [])
                    for keyword in keywords:
                        if "상호" in keyword or "법인" in keyword:
                            extracted_data["company_name"] = keyword.split(":")[-1].strip()
                        elif "사업자" in keyword or "등록번호" in keyword:
                            extracted_data["brn"] = re.sub(r'\D', '', keyword)
                        elif "대표" in keyword:
                            extracted_data["representative"] = keyword.split(":")[-1].strip()
                        elif "주소" in keyword or "소재지" in keyword:
                            extracted_data["address"] = keyword.split(":")[-1].strip()
                
                # 3. 프로필 업데이트
                profile_data = {}
                if extracted_data.get("company_name"):
                    profile_data["company_name"] = extracted_data["company_name"]
                if extracted_data.get("brn"):
                    profile_data["brn"] = extracted_data["brn"]
                if extracted_data.get("representative"):
                    profile_data["representative"] = extracted_data["representative"]
                if extracted_data.get("address"):
                    profile_data["address"] = extracted_data["address"]
                    # Auto-detect location_code from address
                    location_code = profile_service.match_location_code(extracted_data["address"])
                    profile_data["location_code"] = location_code
                
                if not profile_data:
                    raise ValueError("Failed to extract any information from PDF. Please check if the document is a valid business registration certificate")
                
                # Update profile
                profile = await profile_service.create_or_update_profile(
                    db, user_id, profile_data
                )
                
                # 4. 응답 생성
                return {
                    "success": True,
                    "extracted": {
                        "company_name": profile.company_name,
                        "brn": profile.brn,
                        "representative": profile.representative,
                        "address": profile.address,
                    },
                    "profile_updated": True,
                    "message": "Business registration certificate processed successfully"
                }
                
        except Exception as e:
            logger.error(f"Gemini AI analysis failed: {e}", exc_info=True)
            raise ValueError(f"Failed to analyze PDF with AI: {str(e)}")
