"""
test_rag.py

Test the complete RAG pipeline without Flask or PostgreSQL.
"""

from rag import ask_rag


# ==========================================
# Fake Lesson Class
# ==========================================

# Stands in for the real SQLAlchemy Lesson model, since ask_rag()
# only ever reads .notes off each lesson - a plain class with that
# one attribute is enough to test the pipeline in isolation.
class Lesson:

    def __init__(self, notes):
        self.notes = notes


# ==========================================
# Fake Lesson Objects
# ==========================================

lessons = [

    Lesson("Mirror checks have improved significantly."),

    Lesson("Student is still hesitant at roundabouts."),

    Lesson("Parallel parking is now much smoother."),

    Lesson("Emergency stop was completed safely."),

    Lesson("Lane discipline has improved over the last two lessons.")

]


# ==========================================
# Ask a Question
# ==========================================

question = "How is the student doing at roundabouts?"


# ==========================================
# Run RAG
# ==========================================

answer = ask_rag(question, lessons)


# ==========================================
# Print Claude's Response
# ==========================================

print("\nClaude's Answer:\n")

print(answer)