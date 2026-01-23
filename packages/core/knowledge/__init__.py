"""Knowledge base management with Chroma vector DB."""

from __future__ import annotations

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from pydantic import BaseModel, Field

# Document processing imports
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None


class KnowledgeDocument(BaseModel):
    """A document in an agent's knowledge base."""

    id: str
    agent_id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    uploaded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeChunk(BaseModel):
    """A chunk of text from a document."""

    id: str
    document_id: str
    text: str
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeManager:
    """Manages knowledge bases for agents using Chroma."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "knowledge"
            )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize Chroma client with persistent storage
        self._client = chromadb.Client(ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(self.storage_path / "chroma"),
            anonymized_telemetry=False,
        ))

        # Document metadata storage
        self._docs_path = self.storage_path / "documents.json"
        self._documents: dict[str, KnowledgeDocument] = {}
        self._load_documents()

        # Files storage
        self._files_path = self.storage_path / "files"
        self._files_path.mkdir(exist_ok=True)

    def _load_documents(self) -> None:
        """Load document metadata from storage."""
        import json

        if self._docs_path.exists():
            try:
                with open(self._docs_path) as f:
                    data = json.load(f)
                    for doc_data in data.get("documents", []):
                        doc = KnowledgeDocument(**doc_data)
                        self._documents[doc.id] = doc
            except Exception:
                self._documents = {}

    def _save_documents(self) -> None:
        """Save document metadata to storage."""
        import json

        data = {"documents": [doc.model_dump() for doc in self._documents.values()]}
        with open(self._docs_path, "w") as f:
            json.dump(data, f, indent=2)

    def _get_collection(self, agent_id: str) -> chromadb.Collection:
        """Get or create a Chroma collection for an agent."""
        collection_name = f"agent_{agent_id.replace('-', '_')}"
        return self._client.get_or_create_collection(
            name=collection_name,
            metadata={"agent_id": agent_id},
        )

    def _extract_text(self, file_path: Path, file_type: str) -> str:
        """Extract text from a document."""
        if file_type == "txt":
            return file_path.read_text(encoding="utf-8", errors="ignore")

        elif file_type == "pdf" and PdfReader:
            reader = PdfReader(str(file_path))
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            return "\n".join(text_parts)

        elif file_type == "docx" and DocxDocument:
            doc = DocxDocument(str(file_path))
            text_parts = []
            for para in doc.paragraphs:
                text_parts.append(para.text)
            return "\n".join(text_parts)

        else:
            # Try to read as text
            try:
                return file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return ""

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind(".")
                last_newline = chunk.rfind("\n")
                break_point = max(last_period, last_newline)
                if break_point > chunk_size // 2:
                    chunk = chunk[: break_point + 1]
                    end = start + break_point + 1

            chunks.append(chunk.strip())
            start = end - overlap

        return [c for c in chunks if c]

    def add_document(
        self,
        agent_id: str,
        filename: str,
        content: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeDocument:
        """Add a document to an agent's knowledge base."""
        # Determine file type
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

        # Generate document ID
        content_hash = hashlib.md5(content).hexdigest()[:8]
        doc_id = f"{agent_id}_{content_hash}"

        # Save file
        file_path = self._files_path / f"{doc_id}.{ext}"
        file_path.write_bytes(content)

        # Extract text
        text = self._extract_text(file_path, ext)

        # Chunk text
        chunks = self._chunk_text(text)

        # Get collection and add chunks
        collection = self._get_collection(agent_id)

        chunk_ids = []
        chunk_texts = []
        chunk_metadatas = []

        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            chunk_texts.append(chunk_text)
            chunk_metadatas.append({
                "document_id": doc_id,
                "chunk_index": i,
                "filename": filename,
                "agent_id": agent_id,
            })

        if chunk_ids:
            collection.add(
                ids=chunk_ids,
                documents=chunk_texts,
                metadatas=chunk_metadatas,
            )

        # Create document record
        doc = KnowledgeDocument(
            id=doc_id,
            agent_id=agent_id,
            filename=filename,
            file_type=ext,
            file_size=len(content),
            chunk_count=len(chunks),
            metadata=metadata or {},
        )
        self._documents[doc_id] = doc
        self._save_documents()

        return doc

    def list_documents(self, agent_id: str) -> list[KnowledgeDocument]:
        """List all documents for an agent."""
        return [doc for doc in self._documents.values() if doc.agent_id == agent_id]

    def get_document(self, document_id: str) -> KnowledgeDocument | None:
        """Get a document by ID."""
        return self._documents.get(document_id)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the knowledge base."""
        doc = self._documents.get(document_id)
        if not doc:
            return False

        # Delete from Chroma
        collection = self._get_collection(doc.agent_id)
        try:
            # Get all chunk IDs for this document
            results = collection.get(where={"document_id": document_id})
            if results["ids"]:
                collection.delete(ids=results["ids"])
        except Exception:
            pass

        # Delete file
        for ext in ["txt", "pdf", "docx", "doc"]:
            file_path = self._files_path / f"{document_id}.{ext}"
            if file_path.exists():
                file_path.unlink()
                break

        # Remove from metadata
        del self._documents[document_id]
        self._save_documents()

        return True

    def query(
        self,
        agent_id: str,
        query_text: str,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Query an agent's knowledge base."""
        collection = self._get_collection(agent_id)

        try:
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
            )
        except Exception:
            return []

        # Format results
        formatted = []
        if results["documents"] and results["documents"][0]:
            for i, doc_text in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                formatted.append({
                    "text": doc_text,
                    "metadata": metadata,
                    "relevance": 1 - distance,  # Convert distance to relevance
                })

        return formatted

    def clear_agent_knowledge(self, agent_id: str) -> int:
        """Clear all knowledge for an agent."""
        docs = self.list_documents(agent_id)
        count = 0
        for doc in docs:
            if self.delete_document(doc.id):
                count += 1
        return count


# Singleton instance
_knowledge_manager: KnowledgeManager | None = None


def get_knowledge_manager() -> KnowledgeManager:
    """Get the knowledge manager singleton."""
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = KnowledgeManager()
    return _knowledge_manager


__all__ = ["KnowledgeDocument", "KnowledgeManager", "get_knowledge_manager"]
