import sys
import os
import argparse
from bson.objectid import ObjectId

# Ensure we can import from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongo_manager import fs, add_document_record, courses_col, branches_col
from database.vector_manager import insert_document_chunk
from utils.pdf_utils import extract_and_chunk_pdf

def upload_local_document(file_path, course_code, uploader_username="admin_cli"):
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        return

    # 1. Lookup Course Metadata
    print(f"🔍 Looking up metadata for course: {course_code}...")
    course = courses_col.find_one({"course_code": course_code})
    if not course:
        print(f"❌ Error: Course code '{course_code}' not found in database.")
        return
        
    branch_id = course["branch_id"]
    semester = course["semester_number"]
    
    branch = branches_col.find_one({"_id": branch_id})
    if not branch:
        print(f"❌ Error: Associated branch not found.")
        return
        
    department_id = branch["department_id"]

    # 2. Read File
    filename = os.path.basename(file_path)
    print(f"📄 Reading {filename} ({os.path.getsize(file_path) / (1024*1024):.2f} MB)...")
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    # 3. Upload to GridFS
    print("☁️ Uploading binary file to MongoDB GridFS...")
    file_id = fs.put(
        pdf_bytes, 
        filename=filename, 
        department_id=str(department_id), 
        branch_id=str(branch_id), 
        semester=int(semester), 
        course_code=str(course_code)
    )

    # 4. Save to Documents Table
    print("📝 Saving metadata to Documents collection...")
    add_document_record(
        filename=filename,
        gridfs_id=file_id,
        course_code=str(course_code),
        uploader_username=uploader_username,
        department_id=str(department_id),
        branch_id=str(branch_id),
        semester=int(semester)
    )

    # 5. Extract and Chunk for ChromaDB
    print("🧠 Extracting text and generating Vector Embeddings for ChromaDB...")
    chunks = extract_and_chunk_pdf(pdf_bytes, filename=filename)
    
    for i, chunk in enumerate(chunks):
        chunk_id = f"{file_id}_chunk_{i}"
        metadata = {
            "department_id": str(department_id),
            "branch_id": str(branch_id),
            "semester": int(semester),
            "course_code": str(course_code)
        }
        insert_document_chunk(chunk_id, chunk, metadata)
        
        # Print progress every 100 chunks
        if (i + 1) % 100 == 0:
            print(f"   -> Embedded {i + 1} / {len(chunks)} chunks...")

    print(f"✅ Success! Completely processed and embedded {len(chunks)} chunks into ChromaDB.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a document directly to the AI Engine bypassing the web UI.")
    parser.add_argument("file_path", help="Absolute or relative path to the PDF file")
    parser.add_argument("course_code", help="The exact course code (e.g., 20XC34)")
    
    args = parser.parse_args()
    upload_local_document(args.file_path, args.course_code)
