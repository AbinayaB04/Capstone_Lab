import os
from pymongo import MongoClient
import gridfs
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Connect to Local MongoDB or remote URI from .env
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)

# Select the database
db = client['study_mate_db']

# GridFS for storing binary documents
fs = gridfs.GridFS(db)

# Collections
users_col = db['users']
departments_col = db['departments']
branches_col = db['branches']
courses_col = db['courses']
documents_col = db['documents']
chat_sessions_col = db['chat_sessions']

def init_mongo_db():
    """Seed the database with initial multi-tenant context mapping if empty."""
    if departments_col.count_documents({}) == 0:
        print("Seeding initial MongoDB database...")
        
        # 1. Seed Departments
        dept_cs = departments_col.insert_one({"dept_name": "School of Computer Science & Engineering"}).inserted_id
        dept_mech = departments_col.insert_one({"dept_name": "School of Mechanical Engineering"}).inserted_id
        
        # 2. Seed Branches
        branch_cse = branches_col.insert_one({
            "branch_name": "B.E. Computer Science and Engineering", 
            "department_id": dept_cs
        }).inserted_id
        branch_it = branches_col.insert_one({
            "branch_name": "B.Tech Information Technology", 
            "department_id": dept_cs
        }).inserted_id
        
        # 3. Seed Courses
        courses_col.insert_many([
            {"course_code": "CS101", "course_name": "Introduction to Programming", "branch_id": branch_cse, "semester_number": 1},
            {"course_code": "CS301", "course_name": "Data Structures", "branch_id": branch_cse, "semester_number": 3},
            {"course_code": "CS501", "course_name": "Artificial Intelligence", "branch_id": branch_cse, "semester_number": 5},
            {"course_code": "IT302", "course_name": "Web Technologies", "branch_id": branch_it, "semester_number": 3},
        ])
        
        # 4. Seed initial Users
        # Admin
        users_col.insert_one({
            "username": "admin",
            "password_hash": "pass", # Note: Hash passwords in production
            "name": "Super Admin",
            "role": "admin",
            "department_id": None,
            "branch_id": None,
            "semester": None
        })
        
        # Sample Student
        users_col.insert_one({
            "username": "test",
            "password_hash": "1234",
            "name": "Test Student",
            "role": "student",
            "department_id": dept_cs,
            "branch_id": branch_cse,
            "semester": 5
        })

        # Sample Staff
        users_col.insert_one({
            "username": "staff1",
            "password_hash": "pass",
            "name": "Prof. Smith",
            "role": "staff",
            "department_id": dept_cs,
            "branch_id": None,
            "semester": None
        })
        print("MongoDB Seeding Complete.")

def verify_login(username, password):
    user = users_col.find_one({"username": username})
    if user:
        if user.get("locked_out", False):
            return False, "Account locked out due to too many failed attempts. Contact admin."
            
        if "password_hash" in user:
            import bcrypt
            try:
                if bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
                    users_col.update_one({"username": username}, {"$set": {"failed_attempts": 0}})
                    return True, user
                else:
                    failed = user.get("failed_attempts", 0) + 1
                    update_doc = {"failed_attempts": failed}
                    if failed >= 5:
                        update_doc["locked_out"] = True
                    users_col.update_one({"username": username}, {"$set": update_doc})
                    return False, f"Invalid ID or Password. Attempts: {failed}/5"
            except Exception:
                pass # Fall through to False
    return False, "Invalid ID or Password."

def update_password(username, new_password):
    import bcrypt
    try:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
        users_col.update_one({"username": username}, {"$set": {"password_hash": hashed_password}})
        return True
    except Exception as e:
        print(f"Error updating password: {e}")
        return False

def get_user_profile(username):
    return users_col.find_one({"username": username})

def get_departments():
    return list(departments_col.find({}))

def get_branches_by_department(dept_id):
    return list(branches_col.find({"department_id": dept_id}))

def get_courses_by_branch_and_sem(branch_id, sem_num):
    return list(courses_col.find({"branch_id": branch_id, "semester_number": sem_num}))

def add_user(name, user_id, role, dob_str, department_id, branch_id, semester, password):
    try:
        import bcrypt
        if users_col.find_one({"username": user_id}):
            return False, "User ID already exists"
            
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        users_col.insert_one({
            "username": user_id,
            "password_hash": hashed_pw,
            "name": name,
            "role": role.lower(),
            "dob": dob_str,
            "department_id": department_id,
            "branch_id": branch_id,
            "semester": semester
        })
        return True, "Success"
    except Exception as e:
        return False, str(e)

def get_all_users():
    users = list(users_col.find({}))
    for u in users:
        u["_id"] = str(u["_id"])
        if u.get("department_id"):
            d = departments_col.find_one({"_id": u["department_id"]})
            u["department_name"] = d["dept_name"] if d else ""
        else:
            u["department_name"] = ""
            
        if u.get("branch_id"):
            b = branches_col.find_one({"_id": u["branch_id"]})
            u["branch_name"] = b["branch_name"] if b else ""
        else:
            u["branch_name"] = ""
    return users

def delete_user(user_id):
    result = users_col.delete_one({"username": user_id})
    return result.deleted_count > 0

def add_document_record(filename, gridfs_id, course_code, uploader_username, department_id, branch_id, semester):
    import datetime
    documents_col.insert_one({
        "filename": filename,
        "gridfs_id": gridfs_id,
        "course_code": course_code,
        "uploader_username": uploader_username,
        "department_id": department_id,
        "branch_id": branch_id,
        "semester": semester,
        "upload_date": datetime.datetime.now()
    })

def get_documents_by_course(course_code):
    return list(documents_col.find({"course_code": course_code}).sort("upload_date", -1))

def delete_document(doc_id):
    from bson.objectid import ObjectId
    doc = documents_col.find_one({"_id": ObjectId(doc_id)})
    if doc:
        try:
            fs.delete(doc["gridfs_id"])
        except:
            pass
            
        from database.vector_manager import get_collection
        collection = get_collection()
        try:
            collection.delete(where={"file_id": str(doc["gridfs_id"])})
        except Exception as e:
            print(f"Error deleting from ChromaDB: {e}")
            
        documents_col.delete_one({"_id": ObjectId(doc_id)})
        return True
    return False

def get_file_from_gridfs(file_id):
    from bson.objectid import ObjectId
    try:
        if isinstance(file_id, str):
            file_id = ObjectId(file_id)
        return fs.get(file_id).read()
    except Exception as e:
        print(f"Error fetching GridFS file: {e}")
        return None

import datetime

def create_chat_session(username, course_code, branch_id, semester, title):
    result = chat_sessions_col.insert_one({
        "username": username,
        "course_code": course_code,
        "branch_id": branch_id,
        "semester": semester,
        "title": title,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
        "messages": []
    })
    return str(result.inserted_id)

def get_chat_sessions_by_user(username, course_code=None):
    query = {"username": username}
    if course_code:
        query["course_code"] = course_code
    sessions = list(chat_sessions_col.find(query).sort("created_at", -1))
    return sessions

def get_chat_session(session_id):
    from bson.objectid import ObjectId
    try:
        return chat_sessions_col.find_one({"_id": ObjectId(session_id)})
    except:
        return None

def add_message_to_session(session_id, role, content):
    from bson.objectid import ObjectId
    try:
        chat_sessions_col.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"messages": {"role": role, "content": content, "timestamp": datetime.datetime.now(datetime.timezone.utc)}}}
        )
    except:
        pass

def update_chat_session_title(session_id, new_title):
    from bson.objectid import ObjectId
    try:
        chat_sessions_col.update_one({"_id": ObjectId(session_id)}, {"$set": {"title": new_title}})
    except:
        pass

def delete_chat_session(session_id):
    from bson.objectid import ObjectId
    try:
        chat_sessions_col.delete_one({"_id": ObjectId(session_id)})
    except:
        pass

# Initialize seeding on import
init_mongo_db()
