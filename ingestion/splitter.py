from langchain_community.document_loaders.parsers import LanguageParser
from langchain_community.document_loaders.generic import GenericLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter , Language

from langchain_community.document_loaders import DirectoryLoader , TextLoader
from pathlib import Path

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

    def split(self, repo_path):
        all_docs = []

        for suffix, language in language_map.items():
            loader = GenericLoader.from_filesystem(
                repo_path,
                glob=f"**/*{suffix}",
                suffixes = [suffix],
                parser = LanguageParser(parser_threshold = 0)

            )
            try:
                docs = loader.load()
                print(f"Docs to insert: {len(docs)}")
                
                if docs:
                    print(f"First doc type: {type(docs[0])}")
                    print(f"First doc content: {docs[0].page_content[:100]}")
                    print(f"First doc metadata: {docs[0].metadata}")


                if not docs:
                    continue

                splitter = RecursiveCharacterTextSplitter.from_language(
                    language = language,
                    chunk_size = self.chunk_size,
                    chunk_overlap = self.chunk_overlap
                )

                chunks = splitter.split_documents(docs)
                all_docs.extend(chunks)
                print(f"  {suffix}: {len(docs)} docs → {len(chunks)} chunks")
            
            except Exception as e:
                print(f" Skipped {suffix}: {e}")
        

        try:
            md_loader = DirectoryLoader(
                repo_path,
                glob = "**/*.md",
                loader_cls = TextLoader,
                loader_kwargs = {"autodetect_encoding": True}
            )

            md_docs = md_loader.load()

            text_splitter = RecursiveCharacterTextSplitter(
               chunk_size = self.chunk_size,
               chunk_overlap = self.chunk_overlap, 
            )

            md_chunks = text_splitter.split_documents(md_docs)
            all_docs.extend(md_chunks)

        
        except Exception as e:
            print(f"Skipped .md: {e}")

        print(f"\n Total Chunks: {len(all_docs)}")

        

        return all_docs
    



