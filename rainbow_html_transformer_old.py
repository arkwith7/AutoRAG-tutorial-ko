from langchain.schema import Document
from bs4 import BeautifulSoup
from io import StringIO
import pandas as pd
import re

class HTMLToTextWithMarkdownTables:
    def transform_documents(
        self, documents: list[Document], **kwargs
    ) -> list[Document]:
        return [self.transform_document(doc) for doc in documents]

    def transform_document(self, document: Document) -> Document:
        soup = BeautifulSoup(document.page_content, 'html.parser')
        
        # Convert tables to markdown
        for table in soup.find_all('table'):
            markdown_table = self.html_table_to_markdown(table)
            table.replace_with(BeautifulSoup(markdown_table, 'html.parser'))
        
        # Process each element to maintain line breaks
        lines = []
        for element in soup.find_all(text=True):
            if element.parent.name == 'br':
                lines.append('\n')
            elif element.strip():
                lines.append(element.strip())
        
        # Join lines, maintaining original line breaks
        text = '\n'.join(lines)
        
        # Remove extra whitespace within lines, but keep line breaks
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n+', '\n', text).strip()
        
        return Document(page_content=text, metadata=document.metadata)

    def html_table_to_markdown(self, table):
        html_string = str(table)
        html_io = StringIO(html_string)
        df = pd.read_html(html_io)[0]
        return df.to_markdown(index=False)

# Example usage:
# transformer = HTMLToTextWithMarkdownTables()
# transformed_docs = transformer.transform_documents(documents)