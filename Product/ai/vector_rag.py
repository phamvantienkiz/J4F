import os
import uuid
import logging
from typing import List, Dict, Any
import chromadb
from google import genai
from google.genai import errors

logger = logging.getLogger(__name__)

# Base Directory: Product/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMADB_PATH = os.path.join(BASE_DIR, "ai", "data", "chromadb")
os.makedirs(CHROMADB_PATH, exist_ok=True)

# Initialize ChromaDB Client
chroma_client = chromadb.PersistentClient(path=CHROMADB_PATH)
collection = chroma_client.get_or_create_collection(name="chat_history_memory")

# Initialize Gemini Client if API key is provided
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai_client = genai.Client(api_key=api_key)
else:
    genai_client = None
    logger.warning("GEMINI_API_KEY is not set. Using mock embeddings (zeros).")

def get_embedding(text: str) -> List[float]:
    """
    Get 768-dimensional embedding from Gemini text-embedding-004 model.
    Falls back to a vector of zeros if GEMINI_API_KEY is not set or API call fails.
    """
    if genai_client and text.strip():
        try:
            response = genai_client.models.embed_content(
                model="text-embedding-004",
                contents=text
            )
            if response.embeddings:
                return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Error calling Gemini Embedding API: {e}")
    
    # Fallback mock embedding: 768 float values
    return [0.0] * 768

def index_message(conversation_id: str, sender: str, user_id: str, content: str, created_at: str) -> None:
    """
    Index a message into ChromaDB collection.
    """
    # Create the document representation
    doc_text = f"Conversation ID: {conversation_id}\nSender: {sender}\nMessage: {content}\nTimestamp: {created_at}"
    
    embedding = get_embedding(content)
    message_id = str(uuid.uuid4())
    
    metadata = {
        "conversation_id": conversation_id,
        "sender": sender,
        "user_id": user_id,
        "created_at": created_at
    }
    
    collection.add(
        ids=[message_id],
        embeddings=[embedding],
        documents=[doc_text],
        metadatas=[metadata]
    )

def recall_context(user_id: str, query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Query ChromaDB for similar past messages from the same user.
    """
    query_embedding = get_embedding(query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit,
        where={"user_id": user_id}
    )
    
    recalled_items = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results.get("distances", [[]])[0]
        
        for doc, meta, dist in zip(docs, metadatas, distances):
            recalled_items.append({
                "document": doc,
                "metadata": meta,
                "distance": dist
            })
            
    return recalled_items
