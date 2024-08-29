import re
import pandas as pd

class InsuranceDocumentProcessor:
    def __init__(self):
        pass
    
    def parse_document(self, text):
        category_pattern = re.compile(r'제\d{1,2}관\s.+|부표\s*\d+\s+.+', re.IGNORECASE)
        subcategory_pattern = re.compile(r'제\d{1,2}조\s.+')
        
        lines = text.splitlines()
        current_category = ""
        current_subcategory = ""
        chunks = []
        chunk_content = ""

        # 첫번째 라인 여부 구분
        first_line = True
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if first_line:
                first_line = False
                continue

            if category_pattern.match(line):
                if chunk_content:
                    chunks.append({
                        "분류": current_category,
                        "세분류": current_subcategory,
                        "청킹내용": chunk_content.strip()
                    })
                current_category = line
                current_subcategory = ""
                chunk_content = ""
            elif subcategory_pattern.match(line):
                if chunk_content:
                    chunks.append({
                        "분류": current_category,
                        "세분류": current_subcategory,
                        "청킹내용": chunk_content.strip()
                    })
                current_subcategory = line
                chunk_content = line + "\n"
            else:
                chunk_content += line + "\n"
        
        if chunk_content:
            chunks.append({
                "분류": current_category,
                "세분류": current_subcategory,
                "청킹내용": chunk_content.strip()
            })
        
        return chunks
    
    def process_document_to_dataframe(self, text):
        chunks = self.parse_document(text)
        df = pd.DataFrame(chunks)
        return df