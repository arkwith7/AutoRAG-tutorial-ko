from langchain.schema import Document
from bs4 import BeautifulSoup, NavigableString
from io import StringIO
import pandas as pd
import re

class HTMLToMarkdown:
    def transform_documents(self, documents: list[Document], **kwargs) -> list[Document]:
        return [self.transform_document(doc) for doc in documents]

    def transform_document(self, document: Document) -> Document:
        soup = BeautifulSoup(document.page_content, 'html.parser')
        markdown_content = self.html_to_markdown(soup)
        return Document(page_content=markdown_content, metadata=document.metadata)

    def html_to_markdown(self, soup):
        def get_markdown_heading_level(element):
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
                level = get_markdown_heading_level(element)
                return f"{'#' * level} {element.get_text().strip()}\n\n"
            elif element.name == 'br':
                return '\n'
            # elif isinstance(element, NavigableString) and element.strip():
            #     return element.strip() + '\n'
            elif element.name == 'p':
                return self.inline_markdown(element) + '\n\n'
            # ... (other element types processing)
            return ''

        markdown_lines = []
        for element in soup.descendants:
            processed = process_element(element)
            if processed:
                markdown_lines.append(processed)

        # Join lines and remove excessive newlines
        markdown_text = ''.join(markdown_lines)
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)

        return markdown_text.strip()

    def inline_markdown(self, element):
        text = ''
        for child in element.children:
            if child.name == 'strong' or child.name == 'b':
                text += f"**{child.get_text()}**"
            elif child.name == 'em' or child.name == 'i':
                text += f"*{child.get_text()}*"
            elif child.name == 'code':
                text += f"`{child.get_text()}`"
            elif child.name == 'a':
                text += f"[{child.get_text()}]({child.get('href', '')})"
            elif child.name == 'br':
                text += '\n'
            else:
                text += child.get_text() if child.string else self.inline_markdown(child)
        return text

    def html_table_to_markdown(self, table):
        html_string = str(table)
        html_io = StringIO(html_string)
        df = pd.read_html(html_io)[0]
        return df.to_markdown(index=False) + '\n\n'

    def html_list_to_markdown(self, list_element):
        markdown_list = []
        for i, item in enumerate(list_element.find_all('li', recursive=False)):
            prefix = '* ' if list_element.name == 'ul' else f"{i+1}. "
            markdown_list.append(f"{prefix}{self.inline_markdown(item)}")
        return '\n'.join(markdown_list) + '\n\n'

# Example usage:
# transformer = HTMLToMarkdown()
# transformed_docs = transformer.transform_documents(documents)