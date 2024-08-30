from langchain.schema import Document
from bs4 import BeautifulSoup
from io import StringIO
import pandas as pd
import re

class HTMLToTextWithIndentationAndMarkdownTables:
    """
    HTML 문서를 구조화된 텍스트로 변환하는 클래스입니다.
    
    이 클래스는 다음과 같은 기능을 제공합니다:
    1. HTML 요소의 계층 구조에 따른 인덴테이션 적용
    2. font-size 속성에 기반한 추가적인 인덴테이션 조정
    3. HTML 테이블을 마크다운 형식의 테이블로 변환
    
    사용 방법:
    1. 클래스의 인스턴스를 생성합니다.
    2. transform_documents 메서드에 Document 객체의 리스트를 전달합니다.
    3. 변환된 Document 객체의 리스트를 받습니다.
    
    예시:
    transformer = HTMLToTextWithIndentationAndMarkdownTables()
    transformed_docs = transformer.transform_documents(documents)
    
    각 Document 객체의 page_content 속성에 변환된 텍스트가 저장됩니다.
    """

    def transform_documents(self, documents: list[Document], **kwargs) -> list[Document]:
        """
        Document 객체의 리스트를 변환합니다.
        
        :param documents: 변환할 Document 객체의 리스트
        :return: 변환된 Document 객체의 리스트
        """
        return [self.transform_document(doc) for doc in documents]

    def transform_document(self, document: Document) -> Document:
        """
        단일 Document 객체를 변환합니다.
        
        :param document: 변환할 Document 객체
        :return: 변환된 Document 객체
        """
        soup = BeautifulSoup(document.page_content, 'html.parser')
        if soup.body:
            text = self.process_element(soup.body, 0)
        else:
            text = self.process_element(soup, 0)
        text = re.sub(r'\n+', '\n', text).strip()
        return Document(page_content=text, metadata=document.metadata)

    def process_element(self, element, depth):
        """
        HTML 요소를 재귀적으로 처리합니다.
        
        :param element: 처리할 BeautifulSoup 요소
        :param depth: 현재 요소의 깊이
        :return: 처리된 텍스트
        """
        if element.name is None:
            return element.strip() + '\n' if element.strip() else ''

        if element.name == 'table':
            return self.html_table_to_markdown(element) + '\n'

        font_size = self.get_font_size(element)
        indent = self.calculate_indent(depth, font_size)
        
        content = []
        for child in element.children:
            content.append(self.process_element(child, depth + 1))

        text = ''.join(content)
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']:
            text = indent + text.replace('\n', '\n' + indent)
        
        return text + '\n' if text.strip() else ''

    def get_font_size(self, element):
        """
        요소의 font-size 값을 추출합니다.
        
        :param element: BeautifulSoup 요소
        :return: font-size 값 (정수)
        """
        style = element.get('style', '')
        font_size_match = re.search(r'font-size:\s*(\d+)px', style)
        return int(font_size_match.group(1)) if font_size_match else 0

    def calculate_indent(self, depth, font_size):
        """
        요소의 깊이와 font-size에 따라 인덴테이션을 계산합니다.
        
        :param depth: 요소의 깊이
        :param font_size: 요소의 font-size
        :return: 계산된 인덴테이션 문자열
        """
        base_indent = '    ' * depth
        if font_size > 20:
            return ''
        elif font_size > 18:
            return '  '
        else:
            return base_indent

    def html_table_to_markdown(self, table):
        """
        HTML 테이블을 마크다운 형식으로 변환합니다.
        
        :param table: 변환할 HTML 테이블 요소
        :return: 마크다운 형식의 테이블 문자열
        """
        html_string = str(table)
        html_io = StringIO(html_string)
        df = pd.read_html(html_io)[0]
        return df.to_markdown(index=False)

# 사용 예시:
# transformer = HTMLToTextWithIndentationAndMarkdownTables()
# transformed_docs = transformer.transform_documents(documents)