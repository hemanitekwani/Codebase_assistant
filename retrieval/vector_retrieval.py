import os
from ingestion.embedder import Embedder
from pathlib import Path

import cohere


GENERIC_WORDS  = {
    "how" , "does" , "work" , "what" , "is" , "the" , "a" , "an" , "do",
    "where", "why", "when", "which", "who", "can", "could", "would",
    "should", "this", "that", "in", "on", "at", "to", "for", "of",
    "and", "or", "not", "with", "from", "by", "are", "was", "were"

}


class vector_retrieval:
    def __init__(self, collection):
        self.collection = collection
        self.embedder = Embedder()
        self.cohere_client = cohere.Client(os.getenv("COHERE_API_KEY"))


    def rerank_chunks(self, query , results , top_n):
        if not results:
            return results
        
        documents = [r['page_content'] for r in results]


        response = self.cohere_client.rerank( 
            model = "rerank-english-v3.0",
            query = query,
            documents = documents,
            top_n = top_n
        )

        reranked = []

        for hit in response.results:
            doc = results[hit.index]
            doc['rerank_score'] = hit.relevance_score
            reranked.append(doc)
        
        return reranked


    def retrieve(self , query , repo_url , top_k = 5 , mode ="semantic"):
        query_embedding = self.embedder.get_embeddings(query).tolist() 
        
        if mode == 'graph':
            filter_graph = {
                "metadata.repo_url": {"$eq": repo_url},
                "metadata.content_type": {"$eq": "graph_relationship"}
            }

            filter_code = {
                "metadata.repo_url": {"$eq": repo_url},
                "metadata.content_type":{"$ne":"graph_relationship"}
            }

            graph_docs = self._vector_search(query_embedding , filter_graph , top_k)
            code_docs = self._vector_search(query_embedding , filter_code , top_k)

            print(f"Retreived Graph chunks: {graph_docs}")

            return (graph_docs + code_docs)[:top_k]
        

        else:
            filter_all = {"metadata.repo_url": {"$eq": repo_url}}
            results = self._vector_search(query_embedding, filter_all , 20)
            return self._boost_and_rerank(query , results , top_k , repo_url)


    def _vector_search(self,query_embedding , filter , limit):
        pipeline = [
            {
                '$vectorSearch': {
                    'queryVector': query_embedding,
                    'path': 'embedding',
                    'numCandidates': 100,
                    'limit': limit,
                    'index': 'vector_index',
                    'filter': filter
        }           
            },
  
           
        {
                '$project': {
                    '_id': 0,
                    'page_content' : 1,
                    'metadata': 1,
                    "score": {"$meta": "vectorSearchScore"},
                    

                }
            }   

        ]

        return list(self.collection.aggregate(pipeline))

    def _boost_and_rerank(self , query , results , top_k, repo_url):
        final = []

        
        all_docs = self.collection.distinct("metadata.source", {"metadata.repo_url": repo_url})
        
        all_filenames = [Path(src).stem.lower() for src in all_docs]
        
        
        query_words = {
            w.strip("?.,") for w in query.lower().split() if w not in GENERIC_WORDS
        }

        matched_keyword = [file  for file in all_filenames if file in query_words  ]
        
        normal = []
        boosted = []
        
        for r in results:
            source_stem = Path(r['metadata'].get('source' , '')).stem.lower()

            if any(match in source_stem for match in matched_keyword):
                boosted.append(r)

            else:
                normal.append(r)

        final = (normal + boosted)[:top_k]

        
        for r in final:
            print(f" Score: {r['score']:.4f} | File: {Path(r['metadata'].get('source','')).name}")

        
        reranked = self.rerank_chunks(query , final , top_k)

        for r in reranked:
            vector_score = r.get('score' , 0)
            rerank_score = r.get('rerank_score' , 0)
            print(f"Vector : {vector_score} rerank_score: {rerank_score}")


        return reranked





    





















