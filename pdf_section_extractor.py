import re
import os
import click
import pdfplumber
import tempfile
from pdf2image import convert_from_path
import img2pdf
from PIL import Image
import io
import pandas as pd
from collections import defaultdict
from langchain_upstage import UpstageLayoutAnalysisLoader
from langchain.schema import Document
from rainbow_html_transformer import HTMLToTextWithMarkdownTables

def convert_pdf_to_pdf(input_path, output_path):
    """PDF를 이미지로 변환한 후 다시 PDF로 변환합니다."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # PDF를 이미지로 변환
        images = convert_from_path(input_path)
        
        # 이미지를 바이트 스트림으로 변환
        image_bytes = []
        for img in images:
            byte_arr = io.BytesIO()
            img.save(byte_arr, format='PNG')
            image_bytes.append(byte_arr.getvalue())
        
        # 이미지를 PDF로 변환
        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(image_bytes))

def extract_text_with_page_info(pdf_path):
    """UpstageLayoutAnalysisLoader를 사용하여 PDF에서 페이지 정보를 포함한 텍스트를 추출하고 저장합니다."""
    try:
        loader = UpstageLayoutAnalysisLoader(
            pdf_path,
            split="page",
            use_ocr=True,  # OCR 활성화
            # ocr_languages=["eng", "kor"],  # OCR 언어 설정 (영어와 한국어)
            exclude=["annotations"]
        )
        documents = loader.load()
    except KeyError as e:
        print(f"Error processing {pdf_path}: {e}")
        print("Attempting to convert and reprocess the PDF...")
        
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_pdf_path = temp_file.name
        
        # PDF 변환
        convert_pdf_to_pdf(pdf_path, temp_pdf_path)
        
        # 변환된 PDF로 다시 시도
        try:
            loader = UpstageLayoutAnalysisLoader(
                        temp_pdf_path,
                        split="page",
                        use_ocr=True,  # OCR 활성화
                        # ocr_languages=["eng", "kor"],  # OCR 언어 설정 (영어와 한국어)
                        exclude=["annotations"]
                    )
            documents = loader.load()
        except Exception as e:
            print(f"Error processing converted PDF: {e}")
            os.unlink(temp_pdf_path)  # 임시 파일 삭제
            return []  # 빈 리스트 반환 또는 다른 적절한 처리
        
        os.unlink(temp_pdf_path)  # 임시 파일 삭제
    
    text_with_page_info = []
    html_transformer = HTMLToTextWithMarkdownTables()
    
    # PDF 파일 이름 추출 (확장자 제외)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # 저장할 디렉토리 생성
    output_dir = "./processed_txt"
    os.makedirs(output_dir, exist_ok=True)
    
    for doc in documents:
        transformed_doc = html_transformer.transform_documents([doc])[0]
        page_number = transformed_doc.metadata['page']
        text_content = transformed_doc.page_content
        
        # 텍스트 파일로 저장
        output_filename = f"{pdf_name}_Page_{page_number}.txt"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(text_content)
        
        text_with_page_info.append((page_number, text_content))
        print(f"Processed and saved page {page_number} to {output_filename}")

    return text_with_page_info

def split_text_into_sections_with_metadata(text_with_page_info):
    """텍스트를 페이지 및 섹션, 서브 섹션 메타데이터와 함께 분리합니다."""
    sections = []
    
    section_pattern = re.compile(r'^\d+\.\s[^\n]+', re.MULTILINE)
    subsection_pattern = re.compile(r'^\d+\.\d+\.\s[^\n]+', re.MULTILINE)
    
    current_section = None
    current_subsection = None

    for page_num, text in text_with_page_info:
        for line in text.splitlines():
            section_match = section_pattern.match(line)
            subsection_match = subsection_pattern.match(line)

            if section_match:
                current_section = section_match.group().strip()
                current_subsection = None  # 섹션이 변경되면 서브섹션 초기화
                sections.append({
                    'Page': page_num,
                    'Section': current_section,
                    'Subsection': '',
                    'Content': ''
                })
            elif subsection_match and current_section:
                current_subsection = subsection_match.group().strip()
                sections.append({
                    'Page': page_num,
                    'Section': current_section,
                    'Subsection': current_subsection,
                    'Content': ''
                })
            elif current_section:
                if current_subsection:
                    sections[-1]['Content'] += " " + line.strip()
                else:
                    sections[-1]['Content'] += " " + line.strip()

    return sections

def sections_to_dataframe_with_metadata(sections, file_name):
    """섹션과 메타데이터를 포함한 데이터프레임으로 변환합니다."""
    data = []
    for section_data in sections:
        data.append([
            file_name,
            section_data['Page'],
            section_data['Section'],
            section_data['Subsection'],
            section_data['Content'].strip()
        ])
    
    df = pd.DataFrame(data, columns=["File", "Page", "Section", "Subsection", "Content"])
    return df

def save_sections_to_excel(df, output_path):
    """데이터프레임을 엑셀 파일로 저장합니다."""
    df.to_excel(output_path, index=False)

@click.command()
@click.option('--dir_path', type=click.Path(exists=True, dir_okay=True, file_okay=False),
              default=os.path.join(root_dir, 'raw_docs'))
@click.option('--save_path', type=click.Path(exists=False, dir_okay=False, file_okay=True),
              default=os.path.join(root_dir, 'data', 'corpus_new.parquet'))
def main(dir_path: str, save_path: str):
    """디렉토리 내 모든 PDF 파일을 처리하여 결과를 엑셀 파일로 저장합니다."""
    all_dataframes = []
    for file_name in os.listdir(dir_path):
        if file_name.lower().endswith(".pdf"):  # 확장자가 .pdf 또는 .PDF인 경우 처리
            pdf_path = os.path.join(dir_path, file_name)
            text_with_page_info = extract_text_with_page_info(pdf_path)
            sections = split_text_into_sections_with_metadata(text_with_page_info)
            df = sections_to_dataframe_with_metadata(sections, file_name)
            all_dataframes.append(df)
    
    # 모든 데이터프레임을 하나로 합치기
    if all_dataframes:
        
        final_df = pd.concat(all_dataframes, ignore_index=True)
        save_sections_to_excel(final_df, save_path)
    else:
        print("No PDF files found in the specified directory.")


if __name__ == '__main__':
    main()

