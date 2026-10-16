from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from typing import List, Optional
from database.mongo_manager import fs, add_document_record, get_documents_by_course, delete_document as db_delete_document, get_course_by_code
from services.audit_service import log_document_access
from utils.pdf_utils import extract_and_chunk_pdf
from database.vector_manager import insert_document_chunk
from api.dependencies import get_current_user, require_permission, require_role, enforce_tenant_isolation
import uuid
import os

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit
ALLOWED_EXTENSIONS = {".pdf", ".pptx"}

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
    uploader_username: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    current_user: dict = Depends(require_permission("upload_materials"))
):
    # Enforce verified cryptographic identity from JWT Bearer token
    verified_username = current_user.get("username")
    verified_role = current_user.get("role")
    
    # Enforce multi-tenant isolation: verify user cannot upload for another department
    enforce_tenant_isolation(current_user, requested_dept_id=user_dept_id, requested_branch_id=selected_branch_id)
    
    # Course semester consistency validation
    course = get_course_by_code(selected_course_code)
    if course and course.get("semester_number") and int(course["semester_number"]) != int(selected_semester):
        raise HTTPException(
            status_code=400,
            detail=f"Course '{selected_course_code}' belongs to Semester {course['semester_number']}, not Semester {selected_semester}."
        )

    queued_files = []
    for uploaded_file in files:
        # 1. Sanitize filename against directory traversal attacks
        raw_name = uploaded_file.filename or "uploaded_document"
        clean_name = os.path.basename(raw_name)
        ext = os.path.splitext(clean_name)[1].lower()
        
        # 2. Whitelist file extensions
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Security rejection: Invalid file format '{ext}' in '{clean_name}'. Only .pdf and .pptx are permitted."
            )
            
        file_bytes = await uploaded_file.read()
        
        # 3. File size enforcement (DoS prevention)
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Security rejection: File '{clean_name}' exceeds maximum allowed size of 50 MB."
            )
        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Security rejection: File '{clean_name}' is empty (0 bytes)."
            )
            
        # 4. Magic bytes verification (Anti-spoofing)
        if ext == ".pdf" and not file_bytes.startswith(b"%PDF"):
            raise HTTPException(
                status_code=400,
                detail=f"Security rejection: Header signature verification failed for '{clean_name}'. File is not a valid PDF."
            )
        elif ext == ".pptx" and not file_bytes.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=400,
                detail=f"Security rejection: Header signature verification failed for '{clean_name}'. File is not a valid PPTX document."
            )

        background_tasks.add_task(
            process_upload_in_background,
            file_bytes,
            clean_name,
            user_dept_id,
            selected_branch_id,
            selected_semester,
            selected_course_code,
            verified_username,
            verified_role
        )
        queued_files.append(clean_name)
        
    return {"message": "Documents queued for background processing.", "files": queued_files}

@router.get("/course/{course_code}")
async def get_documents(
    course_code: str,
    current_user: dict = Depends(require_permission("view_materials"))
):
    enforce_tenant_isolation(
        current_user,
        requested_course_code=course_code
    )
    docs = get_documents_by_course(course_code)
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        doc["gridfs_id"] = str(doc["gridfs_id"])
    return {"documents": docs}

@router.delete("/{doc_id}")
async def delete_doc(
    doc_id: str,
    current_user: dict = Depends(require_permission("delete_materials"))
):
    if db_delete_document(doc_id):
        log_document_access(current_user.get("username", "unknown"), current_user.get("role", "staff"), doc_id, "delete")
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
def sync_chroma_db(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role(["admin"]))
):
    background_tasks.add_task(process_sync_background)
    return {"message": "Sync started in background."}
