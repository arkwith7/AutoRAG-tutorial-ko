from langchain.schema import Document
from bs4 import BeautifulSoup
from io import StringIO
import pandas as pd
import re

class HTMLToTextWithIndentation:
    def __init__(self):
        self.indentation_map = {
            'h1': 0,
            'h2': 1,
            'h3': 2,
            'h4': 3,
            'h5': 4,
            'h6': 5,
            'p': 1,    # 단락에 대한 기본 들여쓰기
            'ul': 1,   # 목록에 대한 기본 들여쓰기
            'ol': 1,
            'li': 2    # 목록 항목에 대한 기본 들여쓰기
        }

    def transform_document(self, document: Document) -> Document:
        soup = BeautifulSoup(document.page_content, 'html.parser')
        text = self.process_element(soup.body if soup.body else soup)
        text = re.sub(r'\n+', '\n', text).strip()
        return Document(page_content=text, metadata=document.metadata)

    def process_element(self, element, current_indent=''):
        if element.name is None:
            text = element.strip()
            if text:
                return current_indent + text + '\n'
            return ''
        
        if element.name == 'footer':
            return ''

        if element.name == 'table':
            return current_indent + self.html_table_to_markdown(element) + '\n'

        content = []
        new_indent = self.calculate_indent(element, current_indent)

        if element.name == 'li':
            list_prefix = ' ' * (len(new_indent) + 4)  # 목록 항목에 대한 들여쓰기와 함께 출력
            lines = element.get_text(separator='\n').splitlines()
            for line in lines:
                if line.strip():
                    content.append(new_indent + list_prefix + line.strip() + '\n')
        elif element.name == 'p':
            lines = element.get_text(separator='\n').splitlines()
            for line in lines:
                if line.strip():  # 빈 줄 무시
                    content.append(new_indent + '    ' + line.strip() + '\n')
        elif element.name == 'br':
            content.append('\n')
        else:
            for child in element.children:
                child_content = self.process_element(child, new_indent)
                if child_content.strip():
                    content.append(child_content)

        return ''.join(content)

    def calculate_indent(self, element, current_indent):
        if element.name in self.indentation_map:
            indent_level = self.indentation_map[element.name]
            return ' ' * (indent_level * 2)  # 각 레벨당 2칸 들여쓰기 적용
        else:
            return current_indent

    def html_table_to_markdown(self, table):
        html_string = str(table)
        html_io = StringIO(html_string)
        df = pd.read_html(html_io)[0]
        return df.to_markdown(index=False)

    def transform_documents(self, documents):
        combined_text = ""
        for document in documents:
            transformed_doc = self.transform_document(document)
            combined_text += transformed_doc.page_content + "\n\n"
        return combined_text.strip()