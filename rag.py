"""
rag.py
 
This module performs Retrieval-Augmented Generation (RAG).
 
Given a student's question, it retrieves the most relevant lesson
notes and sends only those notes to Claude.
"""
 
from embedding import create_embedding
from config import client, MODEL_NAME, TOP_K
 
from sentence_transformers.util import cos_sim
 
 
# create_embedding() converts text into a vector; client is the
# Claude API client built in config.py; cos_sim compares two
# embedding vectors and returns how semantically similar they are.
 
# ==========================================================
# Retrieve the most relevant lesson notes
# ==========================================================
 
# Ranks every lesson note against the instructor's question and
# returns the most relevant ones. Re-embeds every note on every call
# rather than caching embeddings at write time, which is fine at the
# current note volume but would be worth revisiting if a student's
# notes grow into the hundreds.
def retrieve_notes(question, lessons):
 
    question_vector = create_embedding(question)
 
    scores = []
 
    for lesson in lessons:
 
        lesson_vector = create_embedding(
            lesson.notes
        )
 
        # cos_sim() returns a tensor (the numeric object most AI
        # libraries use to support GPU computation), so .item()
        # unwraps it into a plain Python float.
        similarity = cos_sim(
            question_vector,
            lesson_vector
        ).item()
 
        scores.append(
            (
                similarity,
                lesson.notes
            )
        )
 
    # Sorting tuples compares the first element first, so this sorts
    # by similarity score, highest first - the note text along for
    # the ride is never compared.
    scores.sort(
        reverse=True
    )
 
    return scores[:TOP_K]
 
 
 
# ==========================================================
# Build Claude Context 
# ==========================================================
 
# Joins the retrieved notes into a single block of text to slot into
# the prompt below.
def build_context(top_notes):
 
    context = ""
 
    for score, note in top_notes:
 
        context += note + "\n\n"
 
    return context
 
# ==========================================================
# Ask Claude
# ==========================================================
 
# Ties the pipeline together: retrieve the relevant notes, format
# them into a text block, and send both the notes and the question
# to Claude in a single constrained prompt.
def ask_rag(question, lessons):
 
    top_notes = retrieve_notes(
        question,
        lessons
    )
 
    context = build_context(
        top_notes
    )
 
    prompt = f"""
You are an experienced driving instructor.
 
Use ONLY the lesson notes below.
 
Lesson Notes
 
{context}
 
Instructor Question
 
{question}
"""
 
    response = client.messages.create(
 
        model=MODEL_NAME,
 
        max_tokens=500,
 
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
 
    return response.content[0].text