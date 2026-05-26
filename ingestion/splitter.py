from langchain_community.document_loaders.parsers import LanguageParser
from langchain_text_splitters import RecursiveCharacterTextSplitter , Language
from langchain_core.documents.base import Blob
from langchain_core.documents import Document
from pathlib import Path
import os

language_map = {
    ".py" : Language.PYTHON,
    ".js" : Language.JS,
    ".ts" : Language.JS,
    ".go" : Language.GO,
    ".java": Language.JAVA,

}
class Splitter:
    def __init__(self , chunk_size = 1000 , chunk_overlap = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, raw_docs):
        all_chunks = []

        for doc_dict in raw_docs:
            content = doc_dict.get("page_content", "")
            metadata = doc_dict.get("metadata", {})
            file_path = metadata.get("source", "")

            _, ext = os.path.splitext(file_path)

            try:
                if ext in language_map:
                    language = language_map[ext]

                    blob = Blob.from_data(
                        data=content.encode("utf-8"), 
                        path=file_path
                    )
                    parser = LanguageParser(language=language, parser_threshold=0)
                    parsed_docs = list(parser.lazy_parse(blob))

                    for doc in parsed_docs:
                        doc.metadata.update(metadata)


                    splitter = RecursiveCharacterTextSplitter.from_language(
                        language=language,
                        chunk_size=self.chunk_size,
                        chunk_overlap=self.chunk_overlap
                    )
                
                    chunks = splitter.split_documents(parsed_docs)
                    all_chunks.extend(chunks)


                elif ext == ".md": 
                    lc_docs = Document(page_content=content,metadata=metadata)
                    
                    splitter = RecursiveCharacterTextSplitter(
                        chunk_size = self.chunk_size,
                        chunk_overlap = self.chunk_overlap
                    )

                    chunks = splitter.split_documents([lc_docs])
                    all_chunks.extend(chunks)
                
                else: ## .txt,.env 
                    lc_doc = Document(page_content=content,metadata=metadata)

                    splitter = RecursiveCharacterTextSplitter(
                        chunk_size = self.chunk_size,
                        chunk_overlap = self.chunk_overlap 
                    )

                    chunks = splitter.split_documents([lc_docs])
                    all_chunks.extend(chunks)
            
            except Exception as e:
                print(f"[SPLITTER] Skipped splitting for {file_path}: {e}")
        
        print(f"\n[SPLITTER] Total Meaningful Vector Chunks Generated: {len(all_chunks)}")

        return all_chunks

                