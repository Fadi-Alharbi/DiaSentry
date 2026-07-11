"""
DiaSentry — RAG Knowledge Base (ChromaDB)
===========================================
Initializes and manages a ChromaDB vector store seeded with
ADA clinical guideline chunks for semantic retrieval.

The Recommendation Agent queries this store to retrieve the most
relevant clinical protocols for the patient's current state.
"""

import os
import json
import logging
from typing import List, Dict, Any

import chromadb

from backend.rag.ada_guidelines import ADA_GUIDELINE_CHUNKS

logger = logging.getLogger("DiaSentry.RAG.KnowledgeBase")


class ClinicalKnowledgeBase:
    """
    Vector store backed by ChromaDB for ADA clinical guideline retrieval.

    Uses ChromaDB's built-in default embedding function (all-MiniLM-L6-v2)
    for zero-cost, zero-API-key embeddings.

    Usage:
        kb = ClinicalKnowledgeBase()
        results = kb.retrieve("patient has low blood sugar, what should they eat?")
        # Returns top-k relevant guideline chunks
    """

    def __init__(self, collection_name: str = "ada_guidelines"):
        """Initialize the ChromaDB client and seed the guidelines collection."""
        self._client = chromadb.Client()     # In-memory, no persistence needed
        self._collection_name = collection_name
        self._collection = None
        self._initialized = False

    def initialize(self) -> None:
        """
        Create the collection and seed it with ADA guideline chunks.
        Called once at application startup.
        """
        if self._initialized:
            return

        try:
            # Delete existing collection if it exists (clean start)
            try:
                self._client.delete_collection(self._collection_name)
            except Exception:
                pass

            # Create the collection with default embedding function
            self._collection = self._client.create_collection(
                name=self._collection_name,
                metadata={"description": "ADA Standards of Care clinical guidelines"}
            )

            # Seed with guideline chunks
            all_chunks = list(ADA_GUIDELINE_CHUNKS)

            # Automatically load dynamically extracted JSON chunks if present
            json_path = os.path.join(os.path.dirname(__file__), "ada_2026_extracted.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        extracted_chunks = data.get("chunks", [])
                        if extracted_chunks:
                            all_chunks.extend(extracted_chunks)
                            logger.info(f"📁 Successfully loaded {len(extracted_chunks)} dynamically extracted chunks from {json_path}")
                except Exception as ex:
                    logger.warning(f"⚠️ Could not load {json_path}: {ex}")

            ids = []
            documents = []
            metadatas = []

            for chunk in all_chunks:
                ids.append(chunk["id"])
                documents.append(chunk["content"])
                metadatas.append({"topic": chunk["topic"]})

            self._collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            self._initialized = True
            logger.info(
                f"✅ Knowledge base initialized with {len(all_chunks)} "
                f"total ADA guideline chunks (Static + Dynamic JSON)"
            )

        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {e}", exc_info=True)
            raise

    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve the top-k most relevant guideline chunks for a query.

        Args:
            query: Natural language query describing the clinical situation.
            k: Number of results to return (default: 3).

        Returns:
            List of dicts with keys: 'id', 'topic', 'content', 'relevance_score'
        """
        if not self._initialized or self._collection is None:
            logger.warning("Knowledge base not initialized — call initialize() first")
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(k, self._collection.count()),
                include=["documents", "metadatas", "distances"]
            )

            retrieved = []
            if results and results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    retrieved.append({
                        "id": doc_id,
                        "topic": results["metadatas"][0][i]["topic"],
                        "content": results["documents"][0][i],
                        "relevance_score": 1.0 - (results["distances"][0][i] / 2.0)
                        # ChromaDB distances are L2; convert to 0-1 relevance
                    })

            logger.debug(
                f"RAG retrieved {len(retrieved)} chunks for query: "
                f"'{query[:60]}...'"
            )
            return retrieved

        except Exception as e:
            logger.error(f"RAG retrieval error: {e}", exc_info=True)
            return []

    def retrieve_text(self, query: str, k: int = 3) -> str:
        """
        Convenience method: retrieve and format as a single text block
        for injection into LLM context.
        """
        results = self.retrieve(query, k)
        if not results:
            return "No relevant clinical guidelines found."

        sections = []
        for r in results:
            sections.append(
                f"=== {r['topic']} (relevance: {r['relevance_score']:.2f}) ===\n"
                f"{r['content']}"
            )
        return "\n\n".join(sections)


# ═══════════════════════════════════════════════════════════════
#  Singleton Instance
# ═══════════════════════════════════════════════════════════════

knowledge_base = ClinicalKnowledgeBase()
