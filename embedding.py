"""
embedding.py
 
This module converts human language into embedding vectors.
 
Embedding vectors allow the computer to understand semantic meaning
instead of comparing individual words.
"""
 
from sentence_transformers import SentenceTransformer
# sentence_transformers is a third-party AI library (pip install
# sentence-transformers). SentenceTransformer is a class inside it
# used below to build the actual embedding model.
 
 
# ==========================================================
# Create ONE embedding model
# ==========================================================
 
# Builds the embedding model. "all-MiniLM-L6-v2" is a pre-trained
# model hosted on Hugging Face - it downloads once on first run and
# loads from the local cache on every run after that. Once built,
# embedding_model can convert any text into an embedding vector.
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)
 
# ==========================================================
# Convert text into an embedding vector
# ==========================================================
 
# .encode() converts a piece of text into an embedding vector that
# numerically represents its semantic meaning for similarity search.
# The output is a vector of 384 decimal numbers - not meant to be
# read directly, but compared against other vectors using cosine
# similarity, which is what the RAG retrieval step relies on.
def create_embedding(text):
 
    embedding = embedding_model.encode(text)
 
    return embedding