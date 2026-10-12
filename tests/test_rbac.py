from auth.rbac_manager import RBACManager

def test_admin_permissions():
    assert RBACManager.has_permission("admin", "manage_users") is True
    assert RBACManager.has_permission("admin", "manage_departments") is True
    assert RBACManager.has_permission("admin", "manage_courses") is True
    assert RBACManager.has_permission("admin", "ask_ai") is False

def test_staff_permissions():
    assert RBACManager.has_permission("staff", "upload_materials") is True
    assert RBACManager.has_permission("staff", "view_materials") is True
    assert RBACManager.has_permission("staff", "manage_users") is False

def test_student_permissions():
    assert RBACManager.has_permission("student", "ask_ai") is True
    assert RBACManager.has_permission("student", "download_materials") is True
    assert RBACManager.has_permission("student", "upload_materials") is False

def test_invalid_role():
    assert RBACManager.has_permission("guest", "ask_ai") is False
    assert RBACManager.has_permission("", "ask_ai") is False
    assert RBACManager.has_permission(None, "ask_ai") is False
