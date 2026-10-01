import logging
import os

# Create a logger
audit_logger = logging.getLogger("StudyMateAudit")
audit_logger.setLevel(logging.INFO)

# Create file handler
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

file_handler = logging.FileHandler(os.path.join(log_dir, "audit.log"))
file_handler.setLevel(logging.INFO)

# Create formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the handler to the logger
if not audit_logger.handlers:
    audit_logger.addHandler(file_handler)

def log_login(username, role, status):
    audit_logger.info(f"LOGIN | User: {username} | Role: {role} | Status: {status}")

def log_document_access(user_id, role, doc_id, action):
    audit_logger.info(f"DOCUMENT | User: {user_id} | Role: {role} | Doc: {doc_id} | Action: {action}")

def log_system_event(user_id, role, action, details):
    audit_logger.info(f"SYSTEM | User: {user_id} | Role: {role} | Action: {action} | Details: {details}")

def get_audit_logs_df():
    import pandas as pd
    log_file = os.path.join(log_dir, "audit.log")
    if not os.path.exists(log_file):
        return pd.DataFrame()
        
    data = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" - ", 2)
            if len(parts) == 3:
                timestamp_str, level, message = parts
                msg_parts = [p.strip() for p in message.split("|")]
                event_type = msg_parts[0]
                
                entry = {
                    "timestamp": timestamp_str,
                    "level": level,
                    "event_type": event_type,
                    "user": None,
                    "role": None,
                    "action": None,
                    "status": None,
                    "details": None,
                    "doc": None
                }
                
                for p in msg_parts[1:]:
                    if ":" in p:
                        k, v = p.split(":", 1)
                        entry[k.strip().lower()] = v.strip()
                data.append(entry)
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
    return df
