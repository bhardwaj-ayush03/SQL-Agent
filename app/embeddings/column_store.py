import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings

model = SentenceTransformer(settings.embedding_model)


def card_to_text(card):
    values = ", ".join(str(v) for v in card["sample_values"])
    return f"table {card['table']}, column {card['column']}, type {card['dtype']}, sample values {values}"


class ColumnStore:
    def __init__(self):
        self.cards = []
        self.index = None

    def build(self, column_cards):
        self.cards = column_cards
        texts = [card_to_text(c) for c in column_cards]
        vectors = model.encode(texts)
        vectors = np.array(vectors).astype("float32")

        dim = vectors.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(vectors)

    def search(self, question, top_k=5):
        if self.index is None:
            return []

        query_vector = model.encode([question])
        query_vector = np.array(query_vector).astype("float32")

        distances, indices = self.index.search(query_vector, top_k)
        results = [self.cards[i] for i in indices[0] if i != -1]
        return results
