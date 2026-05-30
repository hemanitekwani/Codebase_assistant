import rustworkx as rx
import uuid


class GraphIndexer:
    def __init__(self, vector_store, session_id):
        self.vector_store = vector_store
        self.session_id = session_id


    def index(self, graph: rx.PyDiGraph, repo_url: str):
        chunks = self._graph_to_chunks(graph, repo_url)

        self._store_chunks(chunks)

        print(f"Indexed {len(chunks)} graph relationship chunks")


    def _graph_to_chunks(self, graph: rx.PyDiGraph, repo_url: str):
        chunks = []

        for idx in graph.node_indices():

            node = graph[idx]
            filename = node["file"]

            imports = [
                graph[i]["file"]
                for i in graph.successor_indices(idx)
            ]

            imported_by = [
                graph[i]["file"]
                for i in graph.predecessor_indices(idx)
            ]

            text = f"""
                File: {filename}
                Language: {node['language']}
                Functions defined: {','.join(node.get('functions', [])) or 'none'}
                Classes defined: {','.join(node.get('classes', [])) or 'none'}
                Directly imports: {','.join(imports) or 'none'}
                Imported by: {','.join(imported_by) or 'none'}
                """

            chunks.append({
                "page_content": text,
                "metadata": {
                    "source": filename,
                    "session_id": str(self.session_id),
                    "repo_url": repo_url,
                    "content_type": "graph_relationship",
                    "language": node["language"]
                }
            })

        return chunks


    def _store_chunks(self, chunks):

        docs = []

        for chunk in chunks:

            text = chunk["page_content"]
            metadata = chunk["metadata"]

            filename = metadata["source"]

            enriched = (
                f"File: {filename} | "
                f"Type: graph_relationship\n\n{text}"
            )

            embedding = (
                self.vector_store
                .embedder
                .get_embeddings(enriched)
                .tolist()
            )

            docs.append({
                "_id": str(uuid.uuid4()),
                "session_id": str(self.session_id),
                "page_content": enriched,
                "embedding": embedding,
                "metadata": metadata
            })

        if docs:
            self.vector_store.collection.insert_many(docs)