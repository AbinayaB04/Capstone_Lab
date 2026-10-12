from database.mongo_manager import (
    add_department, add_branch, add_course, delete_course, 
    departments_col, branches_col, courses_col
)
from bson.objectid import ObjectId

def test_curriculum_crud_operations():
    # 1. Add Department
    test_dept_name = "Test Faculty of Data Engineering"
    departments_col.delete_many({"dept_name": test_dept_name})
    
    ok, dept_id = add_department(test_dept_name)
    assert ok is True
    assert dept_id is not None

    # Duplicate check
    ok_dup, _ = add_department(test_dept_name)
    assert ok_dup is False

    # 2. Add Branch
    test_branch_name = "B.Tech Data Science & Analytics"
    branches_col.delete_many({"branch_name": test_branch_name})
    
    ok_b, branch_id = add_branch(test_branch_name, dept_id)
    assert ok_b is True
    assert branch_id is not None

    # 3. Add Course
    test_course_code = "DS701"
    courses_col.delete_many({"course_code": test_course_code})

    ok_c, course_id = add_course(test_course_code, "Deep Learning Systems", branch_id, 7)
    assert ok_c is True
    assert course_id is not None

    # 4. Delete Course
    del_ok = delete_course(course_id)
    assert del_ok is True

    # Cleanup test department and branch
    branches_col.delete_one({"_id": ObjectId(branch_id)})
    departments_col.delete_one({"_id": ObjectId(dept_id)})
