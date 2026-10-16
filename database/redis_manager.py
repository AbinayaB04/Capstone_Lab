import os
import uuid
import numpy as np
import redis
from redis.commands.search.field import VectorField, TagField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

INDEX_NAME = "idx:semantic_cache"
PREFIX = "cache:"

def get_redis_client():
    return redis.Redis(
        host=REDIS_HOST, 
        port=REDIS_PORT, 
        decode_responses=False,
        socket_timeout=1.0,
        socket_connect_timeout=1.0
    )

import socket
import time

_redis_avail_cache = None

def is_redis_available() -> bool:
    global _redis_avail_cache
    now = time.time()
    if _redis_avail_cache is not None and (now - _redis_avail_cache[1]) < 30.0:
        return _redis_avail_cache[0]
    try:
        with socket.create_connection((REDIS_HOST, REDIS_PORT), timeout=0.05):
            _redis_avail_cache = (True, now)
            return True
    except Exception:
        _redis_avail_cache = (False, now)
        return False

_index_initialized = False

def init_redis_index():
    global _index_initialized
    if _index_initialized or not is_redis_available():
        return
    client = get_redis_client()
    try:
        # Check if index exists
        client.ft(INDEX_NAME).info()
        _index_initialized = True
    except Exception:
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
        except Exception:
            pass
        _index_initialized = True

def check_cache(query_vector: list, course_code: str, threshold: float = 0.90):
    if not is_redis_available():
        return None
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
    if not is_redis_available():
        return
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
    if not is_redis_available():
        return
    client = get_redis_client()
    try:
        client.set(f"blacklist:{token}", "true", ex=expires_in)
    except Exception as e:
        print(f"Redis blacklist error: {e}")

def is_token_blacklisted(token: str) -> bool:
    if not is_redis_available():
        return False
    client = get_redis_client()
    try:
        return client.exists(f"blacklist:{token}") > 0
    except Exception as e:
        print(f"Redis check blacklist error: {e}")
        return False

def set_active_session(username: str, token: str, expires_in: int = 14400):
    """
    Enforces single-device / concurrent session control.
    When a user logs in from a new location, their previous token is revoked immediately.
    """
    if not is_redis_available():
        return
    client = get_redis_client()
    try:
        active_key = f"active_session:{username.lower()}"
        previous_token = client.get(active_key)
        if previous_token:
            prev_token_str = previous_token.decode('utf-8') if isinstance(previous_token, bytes) else str(previous_token)
            if prev_token_str != token:
                # Invalidate the previous session token
                client.set(f"blacklist:{prev_token_str}", "true", ex=expires_in)
        client.set(active_key, token, ex=expires_in)
    except Exception as e:
        print(f"Redis active session tracking error: {e}")

def revoke_user_sessions(username: str, expires_in: int = 14400) -> bool:
    """
    Real-time session killswitch (The Leaver Phase).
    Immediately invalidates active JWTs in Redis when an account is suspended or terminated.
    """
    if not is_redis_available():
        return False
    client = get_redis_client()
    try:
        active_key = f"active_session:{username.lower()}"
        active_token = client.get(active_key)
        if active_token:
            token_str = active_token.decode('utf-8') if isinstance(active_token, bytes) else str(active_token)
            client.set(f"blacklist:{token_str}", "true", ex=expires_in)
            client.delete(active_key)
            return True
        return False
    except Exception as e:
        print(f"Redis revoke user sessions error: {e}")
        return False


