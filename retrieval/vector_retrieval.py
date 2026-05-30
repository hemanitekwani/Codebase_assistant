import os
from ingestion.embedder import Embedder
from pathlib import Path

import cohere
from dotenv import load_dotenv

load_dotenv()





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


    def retrieve(self , query , session_id,user_id , top_k = 5 , mode ="semantic"):
        query_embedding = self.embedder.get_embeddings(query).tolist() 
        safe_session_id = str(session_id)

        if mode == 'graph':
            filter_graph = {
                "metadata.session_id": {"$eq": safe_session_id},
                "metadata.user_id": {"$eq": user_id},
                "metadata.content_type": {"$eq": "graph_relationship"}
            }

            filter_code = {
                "metadata.session_id": {"$eq": safe_session_id},
                "metadata.user_id": {"$eq": user_id},
                "metadata.content_type":{"$ne":"graph_relationship"}
            }

            graph_docs = self._vector_search(query_embedding , filter_graph , top_k)
            code_docs = self._vector_search(query_embedding , filter_code , top_k)

            print(f"Retreived Graph chunks: {graph_docs}")

            return (graph_docs + code_docs)[:top_k]
        

        else:
            filter_all = {"metadata.session_id": {"$eq": safe_session_id},  "metadata.user_id": {"$eq": user_id
            }}
            results = self._vector_search(query_embedding, filter_all , 20)
            return self._boost_and_rerank(query , results , top_k)


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

    def _boost_and_rerank(self , query , results , top_k):
        if not results:
            return []
        
        print(f"Sending {len(results)} chunks to Cohere for reranking")

        
        reranked = self.rerank_chunks(query , results , top_k)

        for r in reranked:
            vector_score = r.get('score' , 0)
            rerank_score = r.get('rerank_score' , 0)
            print(f"Vector : {vector_score} rerank_score: {rerank_score}")


        return reranked





    





















