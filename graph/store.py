import rustworkx as rx
from datetime import datetime

class GraphStore:
    def __init__(self, db):
        self.gb = db["graph_code"]

    
    def save(self , graph , repo_url):
        nodes = []

        for idx in graph.node_indices():
            node = graph[idx]

            nodes.append({
                "id": idx,
                "file": node["file"],
                "path": node["path"],
                "functions": node["functions"],
                "classes": node["classes"],
                "calls": node["calls"],
                "language":node["language"]
            })

        edges = []

        for src, tgt , data in graph.weighted_edge_list():
            edges.append({
                "source":src,
                "target":tgt,
                "type": data["type"],
                "from":data["from"],
                "to": data["to"]
        })

            
        self.gb.update_one(
            {"repo_url": repo_url},
            {
                "$set": {
                    "repo_url": repo_url,
                    "nodes": nodes,
                    "edges": edges,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "updated_at": datetime.now()
                    }
                },
                upsert = True
            )
        print(f"Savedgraph: {len(nodes)} nodes , {len(edges)} edges -> MongoDB")


    
    def load(self , repo_url)-> tuple[rx.PyDiGraph , dict]:
        doc = self.gb.find_one({"repo_url": repo_url})

        if not doc:
            print(f"No graph found for {repo_url}")
            return None, {}
        

        graph = rx.PyDiGraph()
        file_to_index = {}

        sorted_nodes = sorted(doc["nodes"] , key = lambda n:n["id"])

        for node in sorted_nodes:
            idx = graph.add_node({
                "file": node["file"],
                "path": node["path"],
                "functions": node["functions"],
                "classes": node["classes"],
                "calls": node["calls"],
                "language": node["language"]

            })

            file_to_index[node["file"]] = idx
            file_to_index[node["file"].rsplit("." , 1)[0].lower()] = idx

        
        for edge in doc["edges"]:
            graph.add_edge(
                edge["source"],
                edge["target"],
                {
                    "type": edge["type"],
                    "from": edge["from"],
                    "to": edge["to"]
                }
            )

        print(f"Loaded graph: {len(graph.nodes())} nodes , {len(graph.edges())} edges")

        return graph , file_to_index
    

    def exists(self , repo_url:str):
        return self.gb.find_one(
            {"repo_url" : repo_url},
            {"_id": 1}
        ) is not None
        