import os
from dotenv import load_dotenv

load_dotenv()

# Google Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Model configuration
GENERATION_MODEL = "gemini-2.0-flash"
EMBEDDING_MODEL = "gemini-embedding-001"

# Chunking configuration
CHUNK_SIZE = 800          # characters per chunk
CHUNK_OVERLAP = 200       # overlap between chunks

# Retrieval configuration
TOP_K_RESULTS = 5         # number of chunks to retrieve

# File paths
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
VECTOR_STORE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vector_store", "store.json")

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(VECTOR_STORE_PATH), exist_ok=True)
