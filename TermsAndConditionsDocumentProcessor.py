import re
import pandas as pd
from collections import deque

class TermsAndConditionsDocumentProcessor:
    """
    약관 문서를 처리하고 청킹하는 클래스입니다.

    주요 기능:
    1. 약관 문서를 분류(관)와 세분류(조)로 나누어 청킹합니다.
    2. 청킹된 내용을 DataFrame으로 변환합니다.

    사용 방법:
    1. 인스턴스 생성: processor = TermsAndConditionsDocumentProcessor(chunk_size=512, overlap_lines=2)
    2. 문서 처리: df = processor.process_document_to_dataframe(document_text)

    매개변수:
    - chunk_size: 각 청크의 최대 크기 (문자 수)
    - overlap_lines: 청크 간 중복되는 줄 수 (2 이상 5 미만)

    반환값:
    - DataFrame: '분류', '세분류', '청킹내용' 열을 포함하는 DataFrame
    """

    def __init__(self, chunk_size=None, overlap_lines=None):
        self.chunk_size = chunk_size
        if chunk_size is not None and overlap_lines is not None:
            if overlap_lines < 2 or overlap_lines >= 5:
                raise ValueError("중복 라인 수는 2 이상 5 미만이어야 합니다.")
            self.overlap_lines = overlap_lines
        else:
            self.overlap_lines = None

    def parse_document(self, text):
        """
        문서를 파싱하여 청크로 나눕니다.

        매개변수:
        - text: 처리할 문서 텍스트

        반환값:
        - list: 청크 딕셔너리의 리스트
        """
        category_pattern = re.compile(r'제\d{1,2}관\s.+|부표\s*\d+\s+.+', re.IGNORECASE)
        subcategory_pattern = re.compile(r'제\d{1,2}(?:\s*\d+)?조(?:의\d+)?\s.+')
        
        lines = text.splitlines()
        current_category = ""
        current_subcategory = ""
        chunks = []
        chunk_content = []
        current_chunk_size = 0
        overlap_buffer = deque(maxlen=self.overlap_lines if self.overlap_lines else 0)
        initial_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if category_pattern.match(line):
                if initial_content:
                    self._add_chunk(chunks, current_category, current_subcategory, initial_content + chunk_content, overlap_buffer)
                    initial_content = []
                else:
                    self._add_chunk(chunks, current_category, current_subcategory, chunk_content, overlap_buffer)
                current_category = line
                current_subcategory = ""
                chunk_content = []
                current_chunk_size = 0
            elif subcategory_pattern.match(line):
                if initial_content:
                    chunk_content = initial_content + chunk_content
                    initial_content = []
                self._add_chunk(chunks, current_category, current_subcategory, chunk_content, overlap_buffer)
                current_subcategory = line
                chunk_content = [line]
                current_chunk_size = len(line) + 1
            else:
                if not current_category and not current_subcategory:
                    initial_content.append(line)
                else:
                    if self.chunk_size and current_chunk_size + len(line) + 1 > self.chunk_size and chunk_content:
                        self._add_chunk(chunks, current_category, current_subcategory, chunk_content, overlap_buffer)
                        chunk_content = list(overlap_buffer)
                        current_chunk_size = sum(len(l) + 1 for l in chunk_content)
                    chunk_content.append(line)
                    current_chunk_size += len(line) + 1

            if self.overlap_lines:
                overlap_buffer.append(line)

        if initial_content:
            self._add_chunk(chunks, current_category, current_subcategory, initial_content + chunk_content, overlap_buffer)
        else:
            self._add_chunk(chunks, current_category, current_subcategory, chunk_content, overlap_buffer)
        
        return chunks
    
    def _add_chunk(self, chunks, category, subcategory, content, overlap_buffer):
        """
        청크를 리스트에 추가합니다.

        매개변수:
        - chunks: 청크 리스트
        - category: 현재 분류
        - subcategory: 현재 세분류
        - content: 청크 내용
        - overlap_buffer: 중복 라인 버퍼
        """
        if content:
            if not subcategory:
                subcategory = category
            chunk = {
                "분류": category,
                "세분류": subcategory,
                "청킹내용": "\n".join(content).strip()
            }
            if chunk["세분류"] != chunk["청킹내용"] and chunk["분류"].strip() and chunk["세분류"].strip():
                chunks.append(chunk)
            overlap_buffer.clear()
            overlap_buffer.extend(content[-self.overlap_lines:] if self.overlap_lines else [])
    
    def process_document_to_dataframe(self, text):
        """
        문서를 처리하여 DataFrame으로 변환합니다.

        매개변수:
        - text: 처리할 문서 텍스트

        반환값:
        - DataFrame: '분류', '세분류', '청킹내용' 열을 포함하는 DataFrame
        """
        chunks = self.parse_document(text)
        df = pd.DataFrame(chunks)
        # "분류"와 "세분류"가 공백인 행 제거
        df = df[(df['분류'].str.strip() != '') & (df['세분류'].str.strip() != '')]
        return df