# 🚀 ADVANCED IAM CONCEPTS - Beyond Your Current Implementation

## Build on Your Existing System

Your system already has **solid fundamentals**. Here are 12+ advanced IAM concepts you can add:

---

## 📊 WHAT YOU ALREADY HAVE (Excellent Foundation!)

```
✅ Role-Based Access Control (RBAC) - Admin/Staff/Student
✅ Password Complexity Policy - 8+ chars, mixed case, numbers, symbols
✅ Failed Login Lockout - 5 attempts = lock
✅ Admin Unlock Account - Manual override
✅ Admin Force Password Reset - Account recovery
✅ Self-Service Password Change - Settings portal
✅ Bcrypt Password Hashing - Cryptographic security
✅ JWT Session Management - 4-hour expiry
✅ Audit Logging - Event tracking

SCORE: 9/20 IAM concepts implemented (45% coverage)
RATING: ⭐⭐⭐⭐ Solid Foundation!
```

---

## 🎯 NEXT 12 CONCEPTS TO ADD (Prioritized)

### PRIORITY 1: CRITICAL FOR SECURITY ⭐⭐⭐

---

## 1️⃣ MULTI-TENANT DATA ISOLATION (CRITICAL!)

**What it does:** Ensures students from CSE dept CANNOT see ECE materials

### Current State: ❌ NOT EXPLICITLY IMPLEMENTED
### Effort: 2-3 hours | Impact: CRITICAL

```python
# File: database/multi_tenant_manager.py (NEW)

class MultiTenantManager:
    """Enforce strict data isolation by department"""
    
    @staticmethod
    def add_tenant_filter(query: dict, user_data: dict) -> dict:
        """Add tenant filter to MongoDB query"""
        
        # CRITICAL: All queries must include department filter
        if user_data['role'] == 'student':
            # Students: Only their department + branch + semester
            query['department'] = user_data['department']
            query['branch'] = user_data['branch']
            query['semester'] = user_data['semester']
        
        elif user_data['role'] == 'staff':
            # Staff: Only their department
            query['department'] = user_data['department']
        
        # Admin: No filter (sees all)
        
        return query
    
    @staticmethod
    def validate_document_access(user_data: dict, document_data: dict) -> bool:
        """Validate user can access this document"""
        
        if user_data['role'] == 'admin':
            return True  # Admins see all
        
        if user_data['role'] == 'student':
            # Must match department, branch, semester
            return (document_data['department'] == user_data['department'] and
                    document_data['branch'] == user_data['branch'] and
                    document_data['semester'] == user_data['semester'])
        
        if user_data['role'] == 'staff':
            # Must match department
            return document_data['department'] == user_data['department']
        
        return False

# Usage in your views:
from database.multi_tenant_manager import MultiTenantManager

def get_documents(user_data):
    query = {}
    query = MultiTenantManager.add_tenant_filter(query, user_data)
    
    documents = mongo.documents_collection.find(query)
    
    for doc in documents:
        # Validate each document
        if not MultiTenantManager.validate_document_access(user_data, doc):
            continue  # Skip if not allowed
        
        yield doc
```

### Testing Multi-Tenant Isolation:
```python
# Test that CSE student cannot see ECE materials
student_cse = {'role': 'student', 'department': 'CSE', 'branch': 'AI', 'semester': 5}
student_ece = {'role': 'student', 'department': 'ECE', 'branch': 'AI', 'semester': 5}

document = {'department': 'ECE', 'branch': 'AI', 'semester': 5, 'subject': 'DSP'}

# CSE student should NOT access ECE document
assert not MultiTenantManager.validate_document_access(student_cse, document)

# ECE student SHOULD access ECE document
assert MultiTenantManager.validate_document_access(student_ece, document)

print("✅ Multi-tenant isolation verified!")
```

---

## 2️⃣ ATTRIBUTE-BASED ACCESS CONTROL (ABAC)

**What it does:** Fine-grained access based on user + resource + environment attributes

### Current State: ❌ NOT IMPLEMENTED
### Effort: 3-4 hours | Impact: HIGH

```python
# File: auth/abac_engine.py (NEW)

class ABACEngine:
    """Attribute-Based Access Control"""
    
    @staticmethod
    def can_access(user_attrs: dict, resource_attrs: dict, action: str) -> bool:
        """
        Determine access based on attributes
        
        Args:
            user_attrs: {'role': 'student', 'department': 'CSE', 'semester': 5}
            resource_attrs: {'subject': 'ML-301', 'visibility': 'public', 'dept': 'CSE'}
            action: 'view', 'edit', 'delete'
        """
        
        # Rule 1: Same department
        if user_attrs['department'] != resource_attrs['dept']:
            return False
        
        # Rule 2: Student can only VIEW (not edit/delete)
        if user_attrs['role'] == 'student':
            if action in ['edit', 'delete']:
                return False
        
        # Rule 3: Check visibility level
        visibility = resource_attrs.get('visibility', 'public')
        
        if visibility == 'private':
            # Only creator can access
            return user_attrs.get('is_creator') == True
        
        elif visibility == 'staff_only':
            # Only staff and admin
            if user_attrs['role'] not in ['staff', 'admin']:
                return False
        
        # Rule 4: Check time-based access (if applicable)
        if 'accessible_after' in resource_attrs:
            import datetime
            if datetime.datetime.now() < resource_attrs['accessible_after']:
                return False
        
        return True

# Usage in student_view.py:
from auth.abac_engine import ABACEngine

def view_document(doc_id, user_data):
    document = mongo.documents_collection.find_one({'_id': doc_id})
    
    # Check ABAC
    can_access = ABACEngine.can_access(
        user_attrs={
            'role': user_data['role'],
            'department': user_data['department'],
            'semester': user_data['semester'],
            'is_creator': document['uploaded_by'] == user_data['username']
        },
        resource_attrs={
            'subject': document['subject'],
            'visibility': document.get('visibility', 'public'),
            'dept': document['department'],
            'accessible_after': document.get('accessible_after')
        },
        action='view'
    )
    
    if not can_access:
        st.error("❌ You don't have access to this document")
        return
    
    # Show document
    st.write(document['content'])
```

---

## 3️⃣ CONCURRENT SESSION LIMITS

**What it does:** Prevent user from being logged in on multiple devices simultaneously

### Current State: ⚠️ PARTIAL (JWT exists, but no device tracking)
### Effort: 2-3 hours | Impact: MEDIUM

```python
# File: auth/session_manager.py (UPDATE)

import redis
import json
from datetime import datetime

class SessionManager:
    """Enhanced session management"""
    
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.max_concurrent_sessions = 2  # Max 2 devices per user
        self.session_timeout = 14400  # 4 hours
    
    def create_session(self, user_id: str, device_info: dict) -> str:
        """Create new session with device tracking"""
        
        # Check existing sessions
        session_key_pattern = f"session:{user_id}:*"
        existing_sessions = self.redis.keys(session_key_pattern)
        
        # If at max sessions, remove oldest
        if len(existing_sessions) >= self.max_concurrent_sessions:
            oldest_session = min(
                existing_sessions,
                key=lambda s: self.redis.ttl(s)
            )
            self.redis.delete(oldest_session)
            print(f"⚠️ Logged out from {oldest_session} (max sessions reached)")
        
        # Create new session
        import secrets
        session_id = secrets.token_urlsafe(32)
        session_key = f"session:{user_id}:{session_id}"
        
        session_data = {
            'user_id': user_id,
            'device': device_info.get('device_type', 'unknown'),
            'ip_address': device_info.get('ip_address'),
            'user_agent': device_info.get('user_agent'),
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat()
        }
        
        # Store in Redis
        self.redis.setex(
            session_key,
            self.session_timeout,
            json.dumps(session_data)
        )
        
        return session_id
    
    def validate_session(self, user_id: str, session_id: str) -> bool:
        """Validate session is still valid"""
        
        session_key = f"session:{user_id}:{session_id}"
        session_data = self.redis.get(session_key)
        
        if not session_data:
            return False
        
        # Update last activity
        data = json.loads(session_data)
        data['last_activity'] = datetime.now().isoformat()
        
        self.redis.setex(
            session_key,
            self.session_timeout,
            json.dumps(data)
        )
        
        return True
    
    def logout_all_sessions(self, user_id: str):
        """Logout from all devices"""
        
        session_keys = self.redis.keys(f"session:{user_id}:*")
        
        for key in session_keys:
            self.redis.delete(key)
        
        print(f"✅ Logged out from all sessions for {user_id}")

# Usage in app.py:
if st.button("🚪 Logout"):
    session_mgr = SessionManager()
    session_mgr.logout_all_sessions(st.session_state.user['_id'])
    st.session_state.clear()
    st.rerun()
```

---

## 4️⃣ BACKUP CODES FOR ACCOUNT RECOVERY

**What it does:** Generate recovery codes if user loses 2FA access (email/phone)

### Current State: ❌ NOT IMPLEMENTED
### Effort: 2 hours | Impact: MEDIUM

```python
# File: services/backup_codes_service.py (NEW)

import secrets
import hashlib

class BackupCodesService:
    """Generate and validate backup codes for account recovery"""
    
    def generate_backup_codes(self, count: int = 10) -> list:
        """Generate recovery codes"""
        
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()  # 8 char code: ABCD1234
            codes.append(code)
        
        return codes
    
    def hash_backup_code(self, code: str) -> str:
        """Hash backup code for storage"""
        return hashlib.sha256(code.encode()).hexdigest()
    
    def save_backup_codes(self, user_id: str, codes: list):
        """Save hashed backup codes to database"""
        
        hashed_codes = [self.hash_backup_code(code) for code in codes]
        
        mongo.users_collection.update_one(
            {'_id': user_id},
            {'$set': {
                'backup_codes': hashed_codes,
                'backup_codes_generated': datetime.now()
            }}
        )
    
    def verify_backup_code(self, user_id: str, provided_code: str) -> bool:
        """Use backup code to recover account"""
        
        user = mongo.users_collection.find_one({'_id': user_id})
        
        if not user or 'backup_codes' not in user:
            return False
        
        provided_hash = self.hash_backup_code(provided_code)
        
        # Check if backup code exists
        if provided_hash in user['backup_codes']:
            # Remove used code (can only be used once)
            mongo.users_collection.update_one(
                {'_id': user_id},
                {'$pull': {'backup_codes': provided_hash}}
            )
            
            print(f"✅ Backup code used for {user_id}")
            return True
        
        return False

# Usage in login recovery:
def account_recovery_flow():
    st.title("🔐 Account Recovery")
    
    email = st.text_input("Email registered with account")
    
    if st.button("Send Recovery Link"):
        # Send recovery email with backup code option
        pass
    
    recovery_code = st.text_input("Enter backup code (if you have one)")
    
    if recovery_code:
        user = mongo.users_collection.find_one({'email': email})
        
        backup_service = BackupCodesService()
        if backup_service.verify_backup_code(user['_id'], recovery_code):
            st.success("✅ Account recovered! You can now reset your password.")
        else:
            st.error("❌ Invalid backup code")
```

---

### PRIORITY 2: IMPORTANT FOR COMPLIANCE ⭐⭐⭐

---

## 5️⃣ SUSPICIOUS ACTIVITY DETECTION & ALERTS

**What it does:** Detect unusual login patterns and alert admins

### Current State: ❌ NOT IMPLEMENTED
### Effort: 2-3 hours | Impact: HIGH

```python
# File: services/threat_detection_service.py (NEW)

class ThreatDetectionService:
    """Detect suspicious activity"""
    
    @staticmethod
    def detect_unusual_login(user_id: str, ip_address: str) -> dict:
        """
        Detect if login is from unusual location/time
        """
        
        # Get user's login history
        last_logins = list(mongo.audit_logs_collection.find(
            {
                'user_id': user_id,
                'event_type': 'LOGIN_SUCCESS'
            }
        ).sort('timestamp', -1).limit(10))
        
        alerts = []
        
        # Check 1: Multiple failed attempts then success (suspicious)
        failed_attempts = mongo.audit_logs_collection.count_documents({
            'user_id': user_id,
            'event_type': 'LOGIN_FAILED',
            'timestamp': {'$gt': datetime.now() - timedelta(hours=1)}
        })
        
        if failed_attempts >= 3:
            alerts.append({
                'type': 'MULTIPLE_FAILED_ATTEMPTS',
                'severity': 'HIGH',
                'message': f'{failed_attempts} failed login attempts before success'
            })
        
        # Check 2: Login from new IP
        known_ips = set(log.get('ip_address') for log in last_logins)
        
        if ip_address not in known_ips and len(known_ips) > 0:
            alerts.append({
                'type': 'NEW_IP_ADDRESS',
                'severity': 'MEDIUM',
                'message': f'Login from new IP: {ip_address}'
            })
        
        # Check 3: Login outside normal hours
        login_time = datetime.now().hour
        last_login_hours = [log['timestamp'].hour for log in last_logins[:5]]
        
        avg_login_hour = sum(last_login_hours) / len(last_login_hours) if last_login_hours else 12
        
        if abs(login_time - avg_login_hour) > 6:  # More than 6 hours difference
            alerts.append({
                'type': 'UNUSUAL_LOGIN_TIME',
                'severity': 'LOW',
                'message': f'Login at unusual hour: {login_time} (usual: {int(avg_login_hour)})'
            })
        
        # Check 4: Multiple logins in short time
        recent_logins = mongo.audit_logs_collection.count_documents({
            'user_id': user_id,
            'event_type': 'LOGIN_SUCCESS',
            'timestamp': {'$gt': datetime.now() - timedelta(minutes=5)}
        })
        
        if recent_logins > 2:
            alerts.append({
                'type': 'RAPID_LOGIN_ATTEMPTS',
                'severity': 'CRITICAL',
                'message': f'{recent_logins} logins in last 5 minutes'
            })
        
        return {
            'alerts': alerts,
            'risk_level': max([a['severity'] for a in alerts], default='LOW')
        }
    
    @staticmethod
    def send_alerts_to_admin(user_id: str, alerts: list):
        """Notify admin of suspicious activity"""
        
        if not alerts:
            return
        
        # Get admin emails
        admins = mongo.users_collection.find({'role': 'admin'})
        
        for admin in admins:
            # Send email alert
            print(f"📧 Alert sent to {admin['email']}: {alerts}")

# Usage in login:
def handle_login(username, password, ip_address):
    user = authenticate_user(username, password)
    
    if user:
        # Check for threats
        threat_service = ThreatDetectionService()
        threats = threat_service.detect_unusual_login(user['_id'], ip_address)
        
        if threats['alerts']:
            # Log and alert
            threat_service.send_alerts_to_admin(user['_id'], threats['alerts'])
            
            if threats['risk_level'] == 'CRITICAL':
                # Require additional verification
                st.warning("⚠️ Unusual activity detected. Additional verification required.")
                # Ask for 2FA
```

---

## 6️⃣ ACCOUNT DEACTIVATION & DELETION

**What it does:** Allow users to deactivate/delete their accounts

### Current State: ❌ NOT IMPLEMENTED
### Effort: 2 hours | Impact: LOW

```python
# File: services/account_lifecycle_service.py (NEW)

class AccountLifecycleService:
    """Manage account lifecycle"""
    
    @staticmethod
    def deactivate_account(user_id: str, reason: str = None):
        """Temporarily deactivate account"""
        
        mongo.users_collection.update_one(
            {'_id': user_id},
            {'$set': {
                'account_status': 'DEACTIVATED',
                'deactivated_at': datetime.now(),
                'deactivation_reason': reason,
                'can_reactivate': True
            }}
        )
        
        # Logout all sessions
        SessionManager().logout_all_sessions(user_id)
        
        # Log event
        mongo.audit_logs_collection.insert_one({
            'timestamp': datetime.now(),
            'user_id': user_id,
            'event_type': 'ACCOUNT_DEACTIVATED',
            'severity': 'info'
        })
    
    @staticmethod
    def reactivate_account(user_id: str):
        """Reactivate deactivated account"""
        
        mongo.users_collection.update_one(
            {'_id': user_id},
            {'$set': {'account_status': 'ACTIVE'}}
        )
    
    @staticmethod
    def delete_account(user_id: str):
        """Permanently delete account (GDPR compliance)"""
        
        # Anonymize user data
        mongo.users_collection.update_one(
            {'_id': user_id},
            {'$set': {
                'username': f'DELETED_{user_id}',
                'email': None,
                'phone': None,
                'name': 'DELETED_USER',
                'deleted_at': datetime.now(),
                'account_status': 'DELETED'
            }}
        )
        
        # Delete user sessions
        redis = redis.Redis(host='localhost', port=6379)
        session_keys = redis.keys(f"session:{user_id}:*")
        for key in session_keys:
            redis.delete(key)
        
        # Log deletion
        mongo.audit_logs_collection.insert_one({
            'timestamp': datetime.now(),
            'user_id': user_id,
            'event_type': 'ACCOUNT_DELETED',
            'severity': 'warning'
        })

# UI in settings:
def show_account_settings(user_data):
    st.subheader("⚠️ Danger Zone")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔴 Deactivate Account"):
            reason = st.text_input("Why are you deactivating?")
            if st.button("Confirm Deactivation"):
                AccountLifecycleService.deactivate_account(user_data['_id'], reason)
                st.success("Account deactivated. You can reactivate anytime.")
    
    with col2:
        if st.button("💀 Delete Account Permanently"):
            st.warning("⚠️ This cannot be undone!")
            if st.checkbox("I understand, delete my account"):
                AccountLifecycleService.delete_account(user_data['_id'])
                st.success("Account deleted.")
                st.session_state.clear()
```

---

### PRIORITY 3: NICE TO HAVE ⭐⭐

---

## 7️⃣ API RATE LIMITING

```python
# File: middleware/rate_limiter.py (NEW)

from functools import wraps
import time

class RateLimiter:
    """Rate limiting by user/IP"""
    
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379)
    
    def rate_limit(self, max_requests: int, window_seconds: int):
        """Decorator for rate limiting"""
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, user_id=None, ip_address=None, **kwargs):
                # Use either user_id or ip_address as key
                key = f"rate_limit:{user_id or ip_address}"
                
                # Get current count
                current = self.redis.get(key)
                
                if current is None:
                    self.redis.setex(key, window_seconds, 1)
                    return func(*args, user_id=user_id, ip_address=ip_address, **kwargs)
                
                if int(current) >= max_requests:
                    raise Exception(f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds")
                
                # Increment
                self.redis.incr(key)
                
                return func(*args, user_id=user_id, ip_address=ip_address, **kwargs)
            
            return wrapper
        return decorator

# Usage:
limiter = RateLimiter()

@limiter.rate_limit(max_requests=10, window_seconds=60)
def search_documents(user_id):
    # Max 10 searches per minute
    pass
```

---

## 8️⃣ IP WHITELISTING (For Admin/Staff)

```python
# File: auth/ip_whitelist_manager.py (NEW)

class IPWhitelistManager:
    """Whitelist IPs for staff/admin"""
    
    @staticmethod
    def add_ip_to_whitelist(user_id: str, ip_address: str, device_name: str):
        """Add IP to user's whitelist"""
        
        mongo.users_collection.update_one(
            {'_id': user_id},
            {'$push': {'whitelisted_ips': {
                'ip': ip_address,
                'device_name': device_name,
                'added_at': datetime.now()
            }}}
        )
    
    @staticmethod
    def is_ip_whitelisted(user_id: str, ip_address: str) -> bool:
        """Check if IP is whitelisted"""
        
        user = mongo.users_collection.find_one({'_id': user_id})
        
        if not user or 'whitelisted_ips' not in user:
            return False
        
        return any(ip['ip'] == ip_address for ip in user['whitelisted_ips'])
    
    @staticmethod
    def check_ip_access(user_id: str, ip_address: str) -> dict:
        """Check IP access with alerts"""
        
        user = mongo.users_collection.find_one({'_id': user_id})
        
        # If whitelist exists and IP not in it, alert
        if user.get('whitelisted_ips') and not IPWhitelistManager.is_ip_whitelisted(user_id, ip_address):
            return {
                'allowed': False,
                'message': 'Access from new IP. Require 2FA verification.'
            }
        
        return {'allowed': True}
```

---

## 9️⃣ GDPR COMPLIANCE & DATA EXPORT

```python
# File: services/gdpr_service.py (NEW)

class GDPRService:
    """GDPR compliance features"""
    
    @staticmethod
    def export_user_data(user_id: str) -> dict:
        """Export all user data (GDPR right to access)"""
        
        user = mongo.users_collection.find_one({'_id': user_id})
        
        # Remove sensitive fields
        if user:
            del user['password_hash']
        
        # Get user's documents
        documents = list(mongo.documents_collection.find({'uploaded_by': user['username']}))
        
        # Get user's activity
        activity = list(mongo.audit_logs_collection.find({'user_id': user_id}))
        
        export_data = {
            'profile': user,
            'documents': documents,
            'activity': activity,
            'export_date': datetime.now().isoformat()
        }
        
        return export_data
    
    @staticmethod
    def export_as_json(user_id: str) -> str:
        """Export user data as JSON file"""
        
        data = GDPRService.export_user_data(user_id)
        
        return json.dumps(data, default=str, indent=2)

# UI in settings:
def gdpr_compliance(user_data):
    st.subheader("📋 Data & Privacy")
    
    if st.button("📥 Download My Data (GDPR)"):
        data = GDPRService.export_as_json(user_data['_id'])
        st.download_button(
            "Download JSON",
            data,
            f"mydata_{user_data['username']}.json"
        )
```

---

## 🔟 PERMISSION DELEGATION

```python
# File: auth/permission_delegation.py (NEW)

class PermissionDelegation:
    """Allow admins to delegate permissions temporarily"""
    
    @staticmethod
    def delegate_permission(delegating_user: str, target_user: str, 
                          permission: str, duration_hours: int):
        """Grant temporary permission to another user"""
        
        expiry = datetime.now() + timedelta(hours=duration_hours)
        
        mongo.delegated_permissions_collection.insert_one({
            'delegating_user': delegating_user,
            'target_user': target_user,
            'permission': permission,
            'granted_at': datetime.now(),
            'expires_at': expiry,
            'is_active': True
        })
    
    @staticmethod
    def has_delegated_permission(user_id: str, permission: str) -> bool:
        """Check if user has delegated permission"""
        
        perm = mongo.delegated_permissions_collection.find_one({
            'target_user': user_id,
            'permission': permission,
            'is_active': True,
            'expires_at': {'$gt': datetime.now()}
        })
        
        return perm is not None
```

---

## 1️⃣1️⃣ ACCESS REQUEST & APPROVAL WORKFLOW

```python
# File: services/access_request_service.py (NEW)

class AccessRequestService:
    """Students request access, staff approves"""
    
    @staticmethod
    def request_access(student_id: str, document_id: str, reason: str):
        """Student requests access to restricted document"""
        
        mongo.access_requests_collection.insert_one({
            'student_id': student_id,
            'document_id': document_id,
            'reason': reason,
            'status': 'PENDING',
            'requested_at': datetime.now(),
            'reviewed_by': None,
            'reviewed_at': None
        })
    
    @staticmethod
    def approve_request(request_id: str, staff_id: str):
        """Staff approves access request"""
        
        mongo.access_requests_collection.update_one(
            {'_id': request_id},
            {'$set': {
                'status': 'APPROVED',
                'reviewed_by': staff_id,
                'reviewed_at': datetime.now()
            }}
        )
        
        # Grant temporary access (30 days)
        request = mongo.access_requests_collection.find_one({'_id': request_id})
        
        mongo.temporary_access_collection.insert_one({
            'user_id': request['student_id'],
            'document_id': request['document_id'],
            'granted_by': staff_id,
            'granted_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(days=30)
        })
    
    @staticmethod
    def can_access_via_request(student_id: str, document_id: str) -> bool:
        """Check if student has temporary approved access"""
        
        access = mongo.temporary_access_collection.find_one({
            'user_id': student_id,
            'document_id': document_id,
            'expires_at': {'$gt': datetime.now()}
        })
        
        return access is not None
```

---

## 1️⃣2️⃣ COMPLIANCE REPORTING & AUDIT DASHBOARDS

```python
# File: services/compliance_reports.py (NEW)

class ComplianceReports:
    """Generate audit reports for compliance"""
    
    @staticmethod
    def generate_login_report(days: int = 30) -> dict:
        """Generate login activity report"""
        
        start_date = datetime.now() - timedelta(days=days)
        
        logs = mongo.audit_logs_collection.find({
            'event_type': 'LOGIN_SUCCESS',
            'timestamp': {'$gt': start_date}
        })
        
        report = {
            'total_logins': mongo.audit_logs_collection.count_documents({
                'event_type': 'LOGIN_SUCCESS',
                'timestamp': {'$gt': start_date}
            }),
            'unique_users': len(set(log['user_id'] for log in logs)),
            'failed_logins': mongo.audit_logs_collection.count_documents({
                'event_type': 'LOGIN_FAILED',
                'timestamp': {'$gt': start_date}
            }),
            'locked_accounts': mongo.audit_logs_collection.count_documents({
                'event_type': 'ACCOUNT_LOCKED',
                'timestamp': {'$gt': start_date}
            })
        }
        
        return report
    
    @staticmethod
    def generate_access_report(document_id: str, days: int = 30) -> dict:
        """Generate document access report"""
        
        start_date = datetime.now() - timedelta(days=days)
        
        accesses = list(mongo.audit_logs_collection.find({
            'event_type': 'DOCUMENT_ACCESS',
            'document_id': document_id,
            'timestamp': {'$gt': start_date}
        }))
        
        return {
            'document_id': document_id,
            'total_accesses': len(accesses),
            'unique_users': len(set(a['user_id'] for a in accesses)),
            'access_history': accesses
        }

# Admin view for compliance:
def show_compliance_dashboard():
    st.title("📊 Compliance & Audit Reports")
    
    report_type = st.selectbox("Select Report", ["Login Activity", "Document Access", "Security Events"])
    days = st.slider("Days to include", 1, 365, 30)
    
    if report_type == "Login Activity":
        report = ComplianceReports.generate_login_report(days)
        st.json(report)
    
    if st.button("📥 Export Report as CSV"):
        # Export functionality
        pass
```

---

## 📋 IMPLEMENTATION CHECKLIST

```
PRIORITY 1 (CRITICAL - Do First):
☐ Multi-tenant isolation (2-3 hours)
☐ Attribute-Based Access Control (3-4 hours)

PRIORITY 2 (IMPORTANT - Do Soon):
☐ Concurrent session limits (2-3 hours)
☐ Backup codes (2 hours)
☐ Suspicious activity detection (2-3 hours)
☐ Account deactivation (2 hours)

PRIORITY 3 (NICE TO HAVE - Later):
☐ API rate limiting (2 hours)
☐ IP whitelisting (1-2 hours)
☐ GDPR compliance (2 hours)
☐ Permission delegation (1-2 hours)
☐ Access request workflow (2-3 hours)
☐ Compliance reporting (2-3 hours)

TOTAL EFFORT: 24-35 hours (3-5 days for one person)
```

---

## 🎯 RECOMMENDATION

1. **This Week:** Implement MULTI-TENANT ISOLATION (critical!)
2. **Next Week:** Add ABAC + Concurrent session limits
3. **Later:** Add threat detection + compliance features

---

**Status:** ✅ 12 advanced IAM concepts ready for implementation!

Your system foundation is excellent. These additions will make it **enterprise-grade**.

