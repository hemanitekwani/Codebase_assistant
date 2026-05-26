# from os import path
# import os
# from  dotenv import load_dotenv
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_core.prompts import ChatPromptTemplate



# load_dotenv()

# gemini_key = os.getenv('GOOGLE_API_KEY')


# class Generate_response:
#     def __init__(self , model_name = "gemini-2.5-flash"):
#         self.model = model_name
#         self.llm = ChatGoogleGenerativeAI(model = self.model,google_api_key = gemini_key)

#     def generate(self , query , context):
#         prompt = ChatPromptTemplate.from_messages([
#         ("system", """You are a senior software engineer analyzing a codebase.
# Answer the question using ONLY the provided code context.
# Always mention which file the code is from.
# Be concise and technical."""),
#         ("human", "Context:\n{context}\n\nQuestion: {query}")
#     ])
        
#         result = (prompt | self.llm).invoke({
#             "context" : context,
#             "query" : query
#         })

#         return result
    
    


from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama


# model_id = "microsoft/phi-2"


class Generate_response:
    def __init__(self, model_name="llama-3.3-70b-versatile"):
           
        print("Loading model into memory")

        self.llm = ChatOllama(
            model = model_name,
            temperature=0.3,
            num_ctx=2048
        )

    def generate(self, query, context):
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior software engineer analyzing a codebase.
Answer the question using ONLY the provided code context.
Always mention which file the code is from.
Be concise and technical."""),
            ("human", "Context:\n{context}\n\nQuestion: {query}")
        ])

        # safe_context = str(context)[:1500]

        chain = prompt | self.llm

        result = chain.invoke({
            "context": context,
            "query":query
        })

        return result.content


