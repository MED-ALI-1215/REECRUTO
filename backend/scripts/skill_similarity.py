"""
Print how ChromaDB's embedding model scores pairs of skill names, to tune
SKILL_SIMILARITY_THRESHOLD in .env.

    cd backend
    python -m scripts.skill_similarity                       # built-in examples
    python -m scripts.skill_similarity "torch" "pytorch"     # your own pair
"""

import sys

import chromadb

PAIRS = [
    ("torch", "pytorch"),
    ("postgres database", "postgresql"),
    ("k8s", "kubernetes"),
    ("llm orchestration", "langgraph"),
    ("sklearn", "scikit-learn"),
    # should stay below the threshold:
    ("java", "javascript"),
    ("react", "pytorch"),
    ("docker", "excel"),
]


def main() -> None:
    pairs = [tuple(sys.argv[1:3])] if len(sys.argv) == 3 else PAIRS
    client = chromadb.EphemeralClient()
    col = client.get_or_create_collection("tmp", metadata={"hnsw:space": "cosine"})
    targets = sorted({b for _, b in pairs})
    col.add(ids=targets, documents=targets)
    for a, b in pairs:
        dist = col.query(query_texts=[a], n_results=len(targets))
        sim = dict(zip(dist["ids"][0], (1 - d for d in dist["distances"][0])))
        print(f"{a:>22}  ~  {b:<14} similarity = {sim.get(b, 0):.2f}")


if __name__ == "__main__":
    main()
