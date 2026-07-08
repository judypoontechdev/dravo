"""

The embedding model converts the entire sentence into a single 384-dimensional embedding vector. Each number represents one dimension (or coordinate) in the high-dimensional semantic space. 
Individually the numbers have no human-readable meaning, but together they encode the semantic meaning of the sentence. 
In test_embedding.py, we print the first 10 values simply to verify that the embedding model is working correctly—not because those 10 values have a standalone interpretation.

"""

from embedding import create_embedding

# ==========================================================
# Sample lesson note
# ==========================================================

text = "Mirror checks need improvement."

# ==========================================================
# Generate embedding
# ==========================================================

vector = create_embedding(text)

# ==========================================================
# Display results
# ==========================================================

print("Original Text:")
print(text)

print("\nData Type:")
print(type(vector))

print("\nVector Length:")
print(len(vector))

print("\nFirst 10 Dimensions:")
print(vector[:10])
