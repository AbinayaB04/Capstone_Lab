import os
import uuid
import numpy as np
import redis
from redis.commands.search.field import VectorField, TagField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

INDEX_NAME = "idx:semantic_cache"
PREFIX = "cache:"

def get_redis_client():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)

def init_redis_index():
    client = get_redis_client()
    try:
        # Check if index exists
        client.ft(INDEX_NAME).info()
        print(f"Redis index {INDEX_NAME} already exists.")
    except Exception:
        print(f"Creating Redis index {INDEX_NAME}...")
        # Define schema
        schema = (
            TagField("course_code"),
            TextField("cached_answer"),
            VectorField(
                "question_vector",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": 384, # all-MiniLM-L6-v2 dimension
                    "DISTANCE_METRIC": "COSINE"
                }
            )
        )
        
        definition = IndexDefinition(prefix=[PREFIX], index_type=IndexType.HASH)
        
        try:
            client.ft(INDEX_NAME).create_index(fields=schema, definition=definition)
            print(f"Successfully created {INDEX_NAME}")
        except Exception as e:
            print(f"Failed to create Redis index: {e}")

def check_cache(query_vector: list, course_code: str, threshold: float = 0.90):
    client = get_redis_client()
    
    # Convert list of floats to byte array for Redis
    query_vector_bytes = np.array(query_vector, dtype=np.float32).tobytes()
    
    # K-Nearest Neighbors query
    # We want top 1 match where the distance is small (distance = 1 - cosine_similarity)
    # Cosine Similarity > 0.90 means Distance < 0.10
    redis_query = Query(f"(@course_code:{{{course_code}}})=>[KNN 1 @question_vector $vec AS score]")\
        .return_fields("cached_answer", "score")\
        .dialect(2)
        
    try:
        results = client.ft(INDEX_NAME).search(
            redis_query, query_params={"vec": query_vector_bytes}
        )
        
        if results.docs:
            doc = results.docs[0]
            # RediSearch returns score as distance. Smaller is better.
            distance = float(doc.score)
            similarity = 1.0 - distance
            if similarity >= threshold:
                return doc.cached_answer.decode('utf-8') if isinstance(doc.cached_answer, bytes) else doc.cached_answer
    except Exception as e:
        print(f"Redis search error: {e}")
        
    return None

def set_cache(query_vector: list, query_text: str, course_code: str, answer: str):
    client = get_redis_client()
    
    query_vector_bytes = np.array(query_vector, dtype=np.float32).tobytes()
    cache_id = str(uuid.uuid4())
    key = f"{PREFIX}{cache_id}"
    
    mapping = {
        "course_code": course_code,
        "query_text": query_text,
        "cached_answer": answer,
        "question_vector": query_vector_bytes
    }
    
    try:
        # Save as Hash
        client.hset(key, mapping=mapping)
        # Set 30 day TTL (2592000 seconds)
        client.expire(key, 2592000)
    except Exception as e:
        print(f"Redis save error: {e}")

def blacklist_token(token: str, expires_in: int):
    client = get_redis_client()
    try:
        client.set(f"blacklist:{token}", "true", ex=expires_in)
    except Exception as e:
        print(f"Redis blacklist error: {e}")

def is_token_blacklisted(token: str) -> bool:
    client = get_redis_client()
    try:
        return client.exists(f"blacklist:{token}") > 0
    except Exception as e:
        print(f"Redis check blacklist error: {e}")
        return False
