"""
Document Classification Program

This script classifies PDF documents based on their content and predefined keywords.
It extracts text from PDFs, classifies them, and saves the results to an Excel file.

Usage:
    python classify_documents.py

The script requires the following files:
    - document_class.json: JSON file containing document classification keywords
    - raw_docs/: Directory containing PDF files to be classified

Output:
    - document_classification_result.xlsx: Excel file with classification results

Author: [phs]
Date: [2024-08-23]
"""

import os
import json
import re
import tempfile
from pdf2image import convert_from_path
import fitz
import pandas as pd
import time
from langchain_upstage import UpstageLayoutAnalysisLoader
from rainbow_html_transformer import HTMLToTextWithMarkdownTables


# 1. 문서 유형별 키워드 Json 파일 및 PDF 파일 읽기
def load_document_classes(json_path):
    """
    문서 유형별 키워드 Json 파일을 읽어옴
    json_path : 문서 유형별 키워드 Json 파일 경로
    사업방법서 → business_method_document
    상품요약서 → product_summary
    약관 → terms_and_conditions
    반환 : 문서 유형별 키워드 딕셔너리
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        print(f"Loading document classes from {json_path}")
        json_dict = json.load(f)
        print("문서 유형 정의\n",json_dict)
        return json_dict

def get_pdf_files(folder_path):
    """
    PDF 파일 목록을 가져옴
    folder_path : PDF 파일이 있는 폴더 경로
    반환 : PDF 파일 목록
    """
    return [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]

# 2. PDF 문서에서 텍스트 추출
def extract_text_from_pdf(pdf_path, max_pages=3):
    extracted_text = []
    try:
        doc = fitz.open(pdf_path)
        print(f"{pdf_path} 페이지 수", len(doc))

        for page_num in range(max_pages):
            page_content = doc[page_num].get_text()
            extracted_text.append(page_content)
        
        doc.close()
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")

    # print(' '.join(extracted_text))

    return ' '.join(extracted_text)

def extract_text_with_ocr(pdf_path, max_pages=3):
    extracted_text = []
    try:
        # PDF를 이미지로 변환
        images = convert_from_path(pdf_path, first_page=1, last_page=max_pages)
        
        for i, img in enumerate(images):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                img.save(temp_file, format="PNG")
                temp_file_path = temp_file.name
            
            try:
                loader = UpstageLayoutAnalysisLoader(
                    file_path=temp_file_path,
                    use_ocr=True
                )
                documents = loader.load()
                
                html_transformer = HTMLToTextWithMarkdownTables()
                for doc in documents:
                    # HTML 태그 제거
                    transformed_doc = html_transformer.transform_documents([doc])[0]
                    extracted_text.append(transformed_doc.page_content)
            finally:
                os.unlink(temp_file_path)
    
    except Exception as e:
        print(f"Error processing {pdf_path} with OCR: {e}")
    
    return ' '.join(extracted_text)

# 3. 문서 유형 분류
def classify_document(text, document_classes):
    """
    문서 유형 분류
    text : 텍스트
    document_classes : 문서 유형별 키워드
    반환 : 분류된 문서 유형
    """
    for doc_type, keywords in document_classes.items():
        if any(re.search(keyword, text, re.IGNORECASE) for keyword in keywords):
            return keywords[0]  # 키워드 리스트의 첫 번째 값 반환
    return "Unknown"

# 4. & 5. 문서 분류 및 결과 저장
def classify_documents(folder_path, json_path, output_path):
    """
    문서 분류 및 결과 저장
    folder_path : PDF 파일이 있는 폴더 경로
    json_path : 문서 유형별 키워드 Json 파일 경로
    output_path : 분류 결과 엑셀 파일 경로
    """
    print("Starting document classification process...")
    start_time = time.time()
    
    print("Loading document classes...")
    document_classes = load_document_classes(json_path)
    
    print("Getting PDF files...")
    pdf_files = get_pdf_files(folder_path)
    
    print(f"Found {len(pdf_files)} PDF files to process.")
    
    results = []

    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"Processing file {i} of {len(pdf_files)}: {pdf_file}")
        pdf_path = os.path.join(folder_path, pdf_file)
        
        print("Extracting text from PDF...")
        text = extract_text_from_pdf(pdf_path)
        
        print("Classifying document...")
        doc_type = classify_document(text, document_classes)
    
        if doc_type == "Unknown":
            print(f"Document type unknown. Attempting OCR processing for {pdf_file}")
            ocr_text = extract_text_with_ocr(pdf_path)
            doc_type = classify_document(ocr_text, document_classes)
                    
        results.append({'File Name': pdf_file, 'Document Type': doc_type})
        print(f"Classified as: {doc_type}")

    print("Creating DataFrame and saving to Excel...")
    df = pd.DataFrame(results)
    df.to_excel(output_path, index=False)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Classification results saved to {output_path}")
    print(f"Total time taken: {elapsed_time:.2f} seconds")
    return elapsed_time

if __name__ == "__main__":
    print("Document Classification Program Started")
    
    folder_path = "./raw_docs"
    # folder_path = "/mnt/c/Rbrain/PJT/02.\ 제안/01.신한라이프RAG_업스테이지LLM/01.\ 제안요청자료/'신한라이프 테스트 데이터 문서'"
    json_path = "document_class.json"
    output_path = "document_classification_result.xlsx"
    
    total_time = classify_documents(folder_path, json_path, output_path)
    
    print(f"Document Classification Program Completed in {total_time:.2f} seconds")