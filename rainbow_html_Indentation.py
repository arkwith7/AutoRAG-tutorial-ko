from bs4 import BeautifulSoup, NavigableString
from langchain.schema import Document
import re

class HTMLToTextWithIndentation:
    def transform_documents(self, documents: list[Document], **kwargs) -> list[Document]:
        return [self.transform_document(doc) for doc in documents]

    def transform_document(self, document: Document) -> Document:
        soup = BeautifulSoup(document.page_content, 'html.parser')
        text_content = self.html_to_text(soup)
        return Document(page_content=text_content, metadata=document.metadata)

    def html_to_text(self, soup):
        def get_heading_level(element):
            font_size = element.get('style', '')
            font_size_match = re.search(r'font-size:(\d+)px', font_size)
            if font_size_match:
                size = int(font_size_match.group(1))
                if size >= 24:
                    return 1
                elif size >= 20:
                    return 2
                elif size >= 16:
                    return 3
                else:
                    return 4
            return 1  # 기본값

        def process_element(element):
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = get_heading_level(element)
                return f"{'#' * level} {element.get_text().strip()}\n\n", True
            elif element.name == 'br':
                return '\n', False
            elif isinstance(element, NavigableString) and element.strip():
                return element.strip() + '\n', False
            elif element.name == 'p':
                return element.get_text().strip() + '\n\n', False
            # ... (다른 요소 타입 처리)
            return '', False

        text_lines = []
        processed_titles = set()
        for element in soup.descendants:
            processed, is_title = process_element(element)
            if processed:
                if is_title:
                    title_text = processed.strip()
                    if title_text not in processed_titles:
                        text_lines.append(processed)
                        processed_titles.add(title_text)
                else:
                    text_lines.append(processed)

        # 줄 결합 및 과도한 줄바꿈 제거
        text_content = ''.join(text_lines)
        text_content = re.sub(r'\n{3,}', '\n\n', text_content)

        return text_content.strip()