import re
import pandas as pd

class GeneralDocumentChunker:
    """
    일반 문서를 청크로 나누는 클래스입니다.
    문서를 분류, 세분류, 청킹내용으로 구분하여 처리합니다.
    """

    def __init__(self, max_chunk_size=512, overlap_lines=3):
        """
        GeneralDocumentChunker 클래스의 생성자입니다.

        :param max_chunk_size: 각 청크의 최대 크기 (라인 수)
        :param overlap_lines: 청크 간 중복되는 라인 수
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_lines = overlap_lines

    def classify_section(self, line):
        """
        문서의 라인을 분석하여 분류와 세분류를 식별합니다.

        :param line: 분석할 문서의 한 라인
        :return: (section_type, content) 튜플. section_type은 '분류' 또는 '세분류', content는 해당 라인의 내용
        """
        section_patterns = {
            '분류': r'(문서개요|약관\s가이드북|약관\s요약서|주요보험용어\s해설|가입부터\s지급까지\s쉽게\s찾기|제\d{1,2}조\s.+)',
            '세분류': r'(\d+\.\s.+|\([가-힣]\)\s.+)'
        }

        for key, pattern in section_patterns.items():
            if re.match(pattern, line):
                return key, line.strip()

        return None, None

    def parse_document(self, text):
        """
        문서를 파싱하여 청크를 나누기 위한 초기 데이터를 생성합니다.

        :param text: 파싱할 문서 전체 텍스트
        :return: 파싱된 청크 리스트
        """
        lines = text.splitlines()
        current_chunk = {"분류": "", "세분류": "", "청킹내용": []}
        chunks = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            section_type, content = self.classify_section(line)
            if section_type == '분류':
                if current_chunk["분류"]:  # 새로운 분류가 나오면 현재 청크 저장
                    chunks.append(current_chunk)
                    current_chunk = {"분류": content, "세분류": "", "청킹내용": []}
                else:
                    current_chunk["분류"] = content
            elif section_type == '세분류':
                if current_chunk["세분류"]:  # 새로운 세분류가 나오면 현재 청크 저장
                    chunks.append(current_chunk)
                    current_chunk = {"분류": current_chunk["분류"], "세분류": content, "청킹내용": []}
                else:
                    current_chunk["세분류"] = content
            else:
                current_chunk["청킹내용"].append(line)

        if current_chunk["분류"]:  # 마지막 청크 저장
            chunks.append(current_chunk)

        return chunks

    def chunk_document(self, chunks):
        """
        청킹 처리: 청크 사이즈 초과시 중복 라인을 포함한 새로운 청크를 생성합니다.

        :param chunks: parse_document 메서드에서 생성된 초기 청크 리스트
        :return: 최종 처리된 청크 리스트
        """
        chunked_data = []
        buffer = {"분류": "", "세분류": "", "청킹내용": []}
        
        for chunk in chunks:
            current_lines = chunk["청킹내용"]

            if len(buffer["청킹내용"]) + len(current_lines) <= self.max_chunk_size:
                buffer["청킹내용"].extend(current_lines)
            else:
                chunked_data.append(buffer.copy())

                # 중복 라인 포함
                overlap_lines = buffer["청킹내용"][-self.overlap_lines:] if len(buffer["청킹내용"]) >= self.overlap_lines else buffer["청킹내용"]
                buffer["청킹내용"] = overlap_lines + current_lines

            buffer.update({key: chunk[key] for key in ["분류", "세분류"]})
        
        if buffer["청킹내용"]:
            chunked_data.append(buffer)

        # 청킹내용을 다시 하나의 문자열로 변환
        for chunk in chunked_data:
            chunk["청킹내용"] = "\n".join(chunk["청킹내용"])

        return chunked_data

    def process_document_to_dataframe(self, text):
        """
        문서를 처리하여 데이터프레임으로 반환합니다.

        :param text: 처리할 문서 전체 텍스트
        :return: 처리된 문서 정보가 담긴 pandas DataFrame
        """
        chunks = self.parse_document(text)
        chunked_data = self.chunk_document(chunks)
        df = pd.DataFrame(chunked_data)
        return df

# 사용 예시
# insurance_text = """
# ... # 입력된 보험 약관 텍스트 전체를 여기에 넣습니다 ...
# """

# chunker = GeneralDocumentChunker(max_chunk_size=50, overlap_lines=3)  # max_chunk_size는 라인 수로 정의됨
# df = chunker.process_document_to_dataframe(insurance_text)
# print(df)
