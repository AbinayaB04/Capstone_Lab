class RBACManager:
    ROLES = {
        "admin": ["manage_users", "manage_departments", "manage_courses"],
        "department_admin": ["manage_courses", "upload_materials", "view_materials", "delete_materials"],
        "staff": ["upload_materials", "view_materials", "delete_materials"],
        "student": ["view_materials", "download_materials", "ask_ai"]
    }
    
    @classmethod
    def has_permission(cls, user_role, permission):
        if not user_role:
            return False
        
        user_role = user_role.lower()
        if user_role not in cls.ROLES:
            return False
            
        return permission in cls.ROLES[user_role]
