import os
import chromadb

# Initialize persistent ChromaDB local client
db_dir = os.path.dirname(__file__)
chroma_path = os.path.join(db_dir, 'chroma_store')
if not os.path.exists(chroma_path):
    os.makedirs(chroma_path)

chroma_client = chromadb.PersistentClient(path=chroma_path)

def get_or_create_collection(collection_name="study_materials"):
    return chroma_client.get_or_create_collection(name=collection_name)

def insert_document_chunk(chunk_id, text, metadata):
    """
    metadata should include: 
    - department_id (str)
    - branch_id (str)
    - semester (int)
    - course_code (str)
    """
    collection = get_or_create_collection()
    # ChromaDB generates embeddings automatically using the default model (all-MiniLM-L6-v2)
    # Ensure metadata values are correct types for ChromaDB (str, int, float)
    sanitized_metadata = {k: (str(v) if not isinstance(v, (int, float, bool)) else v) for k, v in metadata.items()}
    
    collection.add(
        documents=[text],
        metadatas=[sanitized_metadata],
        ids=[str(chunk_id)]
    )

def search_documents(query_text, department_id, branch_id, course_code, n_results=3):
    collection = get_or_create_collection()
    
    # Metadata pre-filtering with $and
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where={"$and": [{"department_id": str(department_id)}, {"branch_id": str(branch_id)}, {"course_code": str(course_code)}]}
        )
        return results
    except Exception as e:
        print(f"Error querying ChromaDB: {e}")
        return {"documents": [[]]}
