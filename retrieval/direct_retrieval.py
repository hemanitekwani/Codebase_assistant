from ingestion.embedder import Embedder
from pathlib import Path


class FileMatch():
    def __init__(self , collection):
        self.collection = collection
        self.embedder = Embedder()


    def retrieve(self , query , repo_url):
        query_embedding = self.embedder.get_embeddings(query).tolist()
        
        query_lower = query.lower()

        all_sources = self.collection.distinct("metadata.source" , {"metadata.repo_url": repo_url})
        
        all_filenames = {Path(src).stem.lower():  src for src in all_sources}
        
        matched_source = [
            source for stem , source in all_filenames.items()
            if stem in query_lower
        ]

        direct_docs = []

        if matched_source:
            for source in matched_source:
                file_chunks = list(self.collection.find(
                    {
                        "metadata.source" : source,
                        "metadata.repo_url" : repo_url
                    },
                    {"_id": 0 , "page_content": 1 , "metadata": 1}
                ))

                for chunk in file_chunks:
                    chunk['score'] = 1.0

                direct_docs.extend(file_chunks)
                print(f"Direct fetch: {Path(source).name} - {len(file_chunks)} chunks")

        return direct_docs

        


    




