from sentence_transformers import SentenceTransformer
import os

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

class Embedder:
    def __init__(self, model_name = "all-MiniLM-L6-v2"):
        self.model = None
        self.model_name = model_name

        self.load_model()
    

    def load_model(self):
        self.model = SentenceTransformer(self.model_name)


    def get_embeddings(self , text):
        if self.model is None:
            raise ValueError("Model not found")
        
        return self.model.encode(text)
    

    