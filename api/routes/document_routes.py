from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import List, Optional
from database.mongo_manager import fs, add_document_record, get_documents_by_course, delete_document as db_delete_document
from services.audit_service import log_document_access
from utils.pdf_utils import extract_and_chunk_pdf
from database.vector_manager import insert_document_chunk
import uuid

router = APIRouter(prefix="/documents", tags=["documents"])

def process_upload_in_background(file_bytes: bytes, filename: str, user_dept_id: str, selected_branch_id: str, selected_semester: int, selected_course_code: str, uploader_username: str, role: str):
    try:
        file_id = fs.put(
            file_bytes, 
            filename=filename, 
            department_id=str(user_dept_id), 
            branch_id=str(selected_branch_id), 
            semester=int(selected_semester), 
            course_code=str(selected_course_code)
        )
        
        add_document_record(
            filename=filename,
            gridfs_id=file_id,
            course_code=str(selected_course_code),
            uploader_username=uploader_username,
            department_id=str(user_dept_id),
            branch_id=str(selected_branch_id),
            semester=int(selected_semester)
        )
        
        log_document_access(uploader_username, role, filename, "upload")
        
        chunks = extract_and_chunk_pdf(file_bytes, filename=filename)
        for i, (chunk, source) in enumerate(chunks):
            chunk_id = f"{file_id}_chunk_{i}"
            metadata = {
                "department_id": str(user_dept_id),
                "branch_id": str(selected_branch_id),
                "semester": int(selected_semester),
                "course_code": str(selected_course_code),
                "source": source,
                "file_id": str(file_id)
            }
            insert_document_chunk(chunk_id, chunk, metadata)
            
    except Exception as e:
        print(f"Background upload error: {e}")

@router.post("/upload")
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    user_dept_id: str = Form(...),
    selected_branch_id: str = Form(...),
    selected_semester: int = Form(...),
    selected_course_code: str = Form(...),
    uploader_username: str = Form(...),
    role: str = Form(...)
):
    queued_files = []
    for uploaded_file in files:
        file_bytes = await uploaded_file.read()
        background_tasks.add_task(
            process_upload_in_background,
            file_bytes,
            uploaded_file.filename,
            user_dept_id,
            selected_branch_id,
            selected_semester,
            selected_course_code,
            uploader_username,
            role
        )
        queued_files.append(uploaded_file.filename)
        
    return {"message": "Documents queued for background processing.", "files": queued_files}

@router.get("/course/{course_code}")
async def get_documents(course_code: str):
    docs = get_documents_by_course(course_code)
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        doc["gridfs_id"] = str(doc["gridfs_id"])
    return {"documents": docs}

@router.delete("/{doc_id}")
async def delete_doc(doc_id: str):
    if db_delete_document(doc_id):
        return {"message": "Document deleted successfully"}
    raise HTTPException(status_code=404, detail="Document not found or could not be deleted")

def process_sync_background():
    from database.mongo_manager import documents_col
    docs = list(documents_col.find({}))
    for doc in docs:
        try:
            grid_out = fs.get(doc['gridfs_id'])
            file_bytes = grid_out.read()
            
            chunks = extract_and_chunk_pdf(file_bytes, filename=doc['filename'])
            if not chunks:
                continue
                
            for i, (chunk, source) in enumerate(chunks):
                chunk_id = f"{doc['gridfs_id']}_chunk_{i}"
                metadata = {
                    "department_id": str(doc.get('department_id', '')),
                    "branch_id": str(doc.get('branch_id', '')),
                    "semester": int(doc.get('semester', 0)),
                    "course_code": str(doc.get('course_code', '')),
                    "source": str(source),
                    "file_id": str(doc['gridfs_id'])
                }
                insert_document_chunk(chunk_id, chunk, metadata)
        except Exception as e:
            print(f"Sync error for {doc.get('filename')}: {e}")

@router.post("/sync-chroma")
def sync_chroma_db(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_sync_background)
    return {"message": "Sync started in background."}
