# 🔐 2FA (TWO-FACTOR AUTHENTICATION) - EASY SETUP GUIDE

## Simple OTP via Email or SMS for StudyMate AI

**Goal:** Add 2FA to your existing login system in 1-2 hours with minimal setup

---

## 📋 QUICK COMPARISON: Which OTP Method to Choose?

```
╔════════════════════════════════════════════════════════════════╗
║ METHOD          │ DIFFICULTY │ COST  │ SETUP TIME │ BEST FOR  ║
╠════════════════════════════════════════════════════════════════╣
║ Email OTP       │ ⭐ EASY    │ FREE  │ 5 min     │ START HERE║
║ SMS OTP (Twilio)│ ⭐⭐ EASY   │ $$$  │ 15 min    │ LATER     ║
║ Google Authen.  │ ⭐⭐⭐ MED  │ FREE  │ 30 min    │ ADVANCED  ║
╚════════════════════════════════════════════════════════════════╝

RECOMMENDATION: Start with Email OTP → Easiest, free, works now!
```

---

## 🚀 OPTION 1: EMAIL OTP (EASIEST - START HERE!)

### Why Email OTP?
✅ Easiest to implement (works with Gmail)
✅ No paid service needed
✅ Works with your existing infrastructure
✅ Can deploy immediately
❌ User needs to check email (slower)

### Step 1: Install Dependencies (1 minute)

```bash
pip install python-dotenv  # Already have this
pip install redis          # For OTP storage
# No new packages needed!
```

### Step 2: Update Your `.env` File

```env
# Email Configuration
EMAIL_SENDER=your_psgtech_email@gmail.com
EMAIL_PASSWORD=your_app_password  # NOT your Gmail password!
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# OTP Settings
OTP_EXPIRY_MINUTES=5
OTP_LENGTH=6
```

### Step 3: Create Email OTP Service

**File: `services/email_otp_service.py` (NEW)**

```python
import smtplib
import random
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import redis

class EmailOTPService:
    """
    Email-based OTP for 2FA
    Simple, free, easy to implement
    """
    
    def __init__(self):
        # Redis for storing OTPs temporarily
        self.redis_client = redis.Redis(
            host='localhost', 
            port=6379, 
            db=0,
            decode_responses=True
        )
        
        self.email = os.getenv('EMAIL_SENDER')
        self.password = os.getenv('EMAIL_PASSWORD')
        self.smtp_server = os.getenv('EMAIL_SMTP_SERVER')
        self.smtp_port = int(os.getenv('EMAIL_SMTP_PORT', 587))
        self.otp_expiry = int(os.getenv('OTP_EXPIRY_MINUTES', 5))
    
    def generate_otp(self) -> str:
        """
        Generate 6-digit OTP
        Example: 123456
        """
        otp = str(random.randint(100000, 999999))
        return otp
    
    def send_otp_email(self, user_email: str, username: str) -> dict:
        """
        Send OTP to user email
        
        Args:
            user_email: User's email address
            username: User's name/roll number
        
        Returns:
            {'success': True/False, 'message': str}
        """
        
        try:
            # Generate OTP
            otp = self.generate_otp()
            
            # Store in Redis with expiry
            redis_key = f"otp:{user_email}"
            self.redis_client.setex(
                redis_key,
                self.otp_expiry * 60,  # Convert minutes to seconds
                otp
            )
            
            # Create email message
            subject = "StudyMate AI - Your Login OTP Code"
            
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Welcome to StudyMate AI! 🎓</h2>
                    
                    <p>Hi {username},</p>
                    
                    <p>Your 2-Factor Authentication code is:</p>
                    
                    <h1 style="background-color: #f0f0f0; padding: 20px; text-align: center; 
                               letter-spacing: 5px; font-size: 32px;">
                        {otp}
                    </h1>
                    
                    <p style="color: red;"><strong>
                        This code expires in {self.otp_expiry} minutes.
                    </strong></p>
                    
                    <p>If you didn't request this code, please ignore this email.</p>
                    
                    <hr>
                    <p style="font-size: 12px; color: gray;">
                        StudyMate AI - Intelligent Learning Platform<br>
                        PSG College of Technology
                    </p>
                </body>
            </html>
            """
            
            # Send email
            self._send_email(user_email, subject, body)
            
            return {
                'success': True,
                'message': f'OTP sent to {user_email}',
                'otp': otp  # For testing only - remove in production!
            }
        
        except Exception as e:
            print(f"❌ Error sending OTP: {e}")
            return {
                'success': False,
                'message': f'Failed to send OTP: {str(e)}'
            }
    
    def verify_otp(self, user_email: str, otp_code: str) -> bool:
        """
        Verify OTP entered by user
        
        Args:
            user_email: User's email
            otp_code: 6-digit code user entered
        
        Returns:
            True if valid, False if invalid/expired
        """
        
        # Get OTP from Redis
        redis_key = f"otp:{user_email}"
        stored_otp = self.redis_client.get(redis_key)
        
        if not stored_otp:
            print(f"❌ OTP expired or not found for {user_email}")
            return False
        
        # Verify OTP
        if str(stored_otp) == str(otp_code):
            # Delete used OTP
            self.redis_client.delete(redis_key)
            print(f"✅ OTP verified for {user_email}")
            return True
        else:
            print(f"❌ Invalid OTP for {user_email}")
            return False
    
    def _send_email(self, recipient: str, subject: str, body: str):
        """
        Actually send the email via SMTP
        """
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email
        msg['To'] = recipient
        
        # Attach HTML body
        msg.attach(MIMEText(body, 'html'))
        
        # Send via SMTP
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()  # Secure connection
            server.login(self.email, self.password)
            server.send_message(msg)
        
        print(f"✅ Email sent to {recipient}")


# Test function
def test_email_otp():
    """Test email OTP functionality"""
    
    service = EmailOTPService()
    
    # Test email
    test_email = "student@example.com"
    
    print("📧 Sending OTP...")
    result = service.send_otp_email(test_email, "John Doe")
    print(f"Result: {result}")
    
    if result['success']:
        # For testing, use the OTP from result
        test_otp = result['otp']
        
        print(f"\n✅ Testing OTP verification with: {test_otp}")
        verified = service.verify_otp(test_email, test_otp)
        print(f"Verified: {verified}")

if __name__ == "__main__":
    test_email_otp()
```

### Step 4: Update Your Login Flow

**File: `views/login_view.py` (UPDATE)**

```python
import streamlit as st
from services.email_otp_service import EmailOTPService

def show_login():
    """Updated login with 2FA"""
    
    st.title("🔐 StudyMate AI Login")
    
    # Initialize session state
    if 'login_step' not in st.session_state:
        st.session_state.login_step = 'credentials'  # credentials or otp
    
    if 'temp_user' not in st.session_state:
        st.session_state.temp_user = None
    
    # STEP 1: Username & Password
    if st.session_state.login_step == 'credentials':
        show_credentials_form()
    
    # STEP 2: OTP Verification
    elif st.session_state.login_step == 'otp':
        show_otp_form()


def show_credentials_form():
    """First step: Username and password"""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Step 1: Enter Your Credentials")
        
        username = st.text_input(
            "📧 Roll Number / Username",
            placeholder="e.g., 19CSE001"
        )
        
        password = st.text_input(
            "🔑 Password",
            type="password",
            placeholder="Enter your password"
        )
        
        if st.button("✅ Next (Send OTP)", key="next_btn", use_container_width=True):
            
            # Validate credentials against MongoDB
            from database.mongo_manager import MongoManager
            mongo = MongoManager()
            
            user = mongo.authenticate_user(username, password)
            
            if user:
                # User authenticated
                # Now send OTP
                
                email_otp = EmailOTPService()
                
                st.info("📧 Sending OTP to your email...")
                result = email_otp.send_otp_email(
                    user_email=user.get('email'),
                    username=user.get('name', username)
                )
                
                if result['success']:
                    # Save user temporarily
                    st.session_state.temp_user = user
                    st.session_state.login_step = 'otp'
                    
                    st.success(f"✅ {result['message']}")
                    st.rerun()
                else:
                    st.error(f"❌ {result['message']}")
            else:
                st.error("❌ Invalid username or password")


def show_otp_form():
    """Second step: OTP verification"""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Step 2: Verify OTP")
        
        user = st.session_state.temp_user
        
        st.info(f"📧 OTP sent to {user.get('email')}")
        st.warning("⏱️ OTP expires in 5 minutes")
        
        otp_code = st.text_input(
            "🔢 Enter 6-digit OTP",
            placeholder="000000",
            max_chars=6
        )
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("✅ Verify OTP", use_container_width=True):
                
                if len(otp_code) != 6:
                    st.error("❌ OTP must be 6 digits")
                else:
                    # Verify OTP
                    email_otp = EmailOTPService()
                    
                    if email_otp.verify_otp(user.get('email'), otp_code):
                        # OTP verified! User is logged in
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.session_state.role = user.get('role')
                        
                        st.success(f"✅ Welcome, {user.get('name')}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid or expired OTP")
        
        with col_b:
            if st.button("🔄 Resend OTP", use_container_width=True):
                
                email_otp = EmailOTPService()
                result = email_otp.send_otp_email(
                    user_email=user.get('email'),
                    username=user.get('name', 'User')
                )
                
                if result['success']:
                    st.success(f"✅ {result['message']}")
                    st.rerun()
                else:
                    st.error(f"❌ {result['message']}")

if __name__ == "__main__":
    show_login()
```

### Step 5: Update Main App

**File: `app.py` (UPDATE)**

```python
import streamlit as st
from views.login_view import show_login
from views.admin_view import show_admin_view
from views.staff_view import show_staff_view
from views.student_view import show_student_view

def main():
    st.set_page_config(
        page_title="StudyMate AI",
        page_icon="🎓",
        layout="wide"
    )
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Check if user is logged in
    if not st.session_state.authenticated:
        show_login()
    else:
        # User is authenticated
        user = st.session_state.user
        role = st.session_state.role
        
        # Sidebar with logout
        with st.sidebar:
            st.write(f"👤 **{user.get('name')}**")
            st.write(f"📍 {role.upper()}")
            
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user = None
                st.rerun()
        
        # Show appropriate view based on role
        if role == 'admin':
            show_admin_view(user)
        elif role == 'staff':
            show_staff_view(user)
        elif role == 'student':
            show_student_view(user)

if __name__ == "__main__":
    main()
```

---

## 🔧 SETUP: Gmail Configuration (5 minutes)

Your Gmail account needs an "App Password" for security. Here's how:

### Step 1: Enable 2-Factor Authentication on Your Gmail Account
1. Go to: https://myaccount.google.com
2. Click "Security" (left menu)
3. Enable "2-Step Verification"

### Step 2: Create App Password
1. Go to: https://myaccount.google.com/apppasswords
2. Select: Mail & Windows
3. Select your device
4. Google will generate a 16-character password
5. Copy it and paste in `.env`:

```env
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx  # The generated password
```

**That's it!** Your email OTP is now ready to use.

---

## 📧 OPTION 2: SMS OTP (OPTIONAL - MORE ADVANCED)

### Why SMS OTP?
✅ More secure than email (harder to intercept)
✅ Faster (SMS is instant)
✅ Better UX for mobile
❌ Requires paid service (Twilio)
❌ More setup

### Setup Twilio (SMS OTP Service)

**Cost:** ~$1-2/month (very cheap!)

#### Step 1: Create Twilio Account
1. Go to: https://www.twilio.com/console
2. Sign up (free account)
3. Verify your phone number
4. Get your: Account SID, Auth Token, Phone Number

#### Step 2: Add to `.env`
```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio number
```

#### Step 3: SMS OTP Service

```python
# File: services/sms_otp_service.py

from twilio.rest import Client
import os
import random
import redis

class SMSOTPService:
    """SMS-based OTP using Twilio"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        self.client = Client(self.account_sid, self.auth_token)
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    def send_otp_sms(self, phone_number: str) -> dict:
        """Send OTP via SMS"""
        
        try:
            otp = str(random.randint(100000, 999999))
            
            # Store in Redis
            self.redis_client.setex(f"otp:sms:{phone_number}", 300, otp)
            
            # Send SMS
            message = self.client.messages.create(
                body=f"Your StudyMate AI 2FA code is: {otp}. Valid for 5 minutes.",
                from_=self.twilio_number,
                to=phone_number
            )
            
            return {
                'success': True,
                'message': f'OTP sent to {phone_number}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def verify_otp_sms(self, phone_number: str, otp_code: str) -> bool:
        """Verify SMS OTP"""
        stored_otp = self.redis_client.get(f"otp:sms:{phone_number}")
        
        if stored_otp and str(stored_otp) == str(otp_code):
            self.redis_client.delete(f"otp:sms:{phone_number}")
            return True
        return False
```

---

## ✅ TESTING YOUR 2FA SETUP

### Test 1: Send OTP via Email

```bash
# Run this in Python console
from services.email_otp_service import EmailOTPService

service = EmailOTPService()
result = service.send_otp_email("your_email@example.com", "Test User")
print(result)
# Should output: {'success': True, 'message': 'OTP sent to...', 'otp': '123456'}
```

### Test 2: Verify OTP

```bash
from services.email_otp_service import EmailOTPService

service = EmailOTPService()
verified = service.verify_otp("your_email@example.com", "123456")
print(verified)  # Should be True
```

### Test 3: Full Login Flow

1. Run your Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Enter credentials
3. Check your email for OTP
4. Enter OTP code
5. You should be logged in!

---

## 🎯 QUICK CHECKLIST

```
✅ BEFORE USING 2FA:

SETUP:
☐ Install redis: pip install redis
☐ Install python-dotenv: pip install python-dotenv
☐ Update .env with email settings
☐ Create Gmail App Password (5 minutes)

CODE:
☐ Create services/email_otp_service.py
☐ Update views/login_view.py
☐ Update app.py

TESTING:
☐ Test email sending
☐ Test OTP verification
☐ Test full login flow

DEPLOYMENT:
☐ Don't hardcode credentials
☐ Use .env for all secrets
☐ Keep Redis running in production
```

---

## 📱 OPTIONAL: Add Phone Number Field

Update MongoDB user schema:

```python
# In database/mongo_manager.py

users_collection.insert_one({
    'username': username,
    'password_hash': hashed_password,
    'email': email,
    'phone_number': '+91XXXXXXXXXX',  # NEW
    'two_fa_method': 'email',  # 'email' or 'sms'
    'two_fa_enabled': True,
    'role': 'student'
})
```

Then in admin view, let users choose:

```python
# In views/admin_view.py

col1, col2 = st.columns(2)
with col1:
    two_fa_method = st.radio(
        "2FA Method",
        ["Email", "SMS"]
    )
with col2:
    if two_fa_method == "SMS":
        phone = st.text_input("Phone Number", "+91")
```

---

## 🚀 DEPLOYMENT NOTES

### For Local Development:
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Run Streamlit
streamlit run app.py
```

### For Production:
```yaml
# docker-compose.yml

services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
  
  streamlit:
    build: .
    depends_on:
      - redis
    environment:
      - EMAIL_SENDER=${EMAIL_SENDER}
      - EMAIL_PASSWORD=${EMAIL_PASSWORD}
```

---

## 💡 QUICK SUMMARY

| Feature | Email OTP | SMS OTP |
|---------|-----------|---------|
| **Setup Time** | 5 min | 15 min |
| **Cost** | FREE | ~$1/month |
| **Difficulty** | ⭐ Easy | ⭐⭐ Medium |
| **Use Email** | YES | Optional |
| **Use Phone** | NO | YES |
| **Best For** | Immediate use | Production |

---

## 🎓 NEXT STEPS

1. **This Hour:** Setup email OTP (5 min Gmail setup + 30 min coding)
2. **Tomorrow:** Test 2FA with all user roles
3. **Later:** Consider SMS OTP for production

**Total time to add 2FA: 1-2 hours!** ⏰

---

**Status:** ✅ Complete 2FA implementation guide ready!

You now have 2 options:
- 🎯 **Email OTP** (START HERE - Easiest, free, works now!)
- 📱 **SMS OTP** (Later - More secure, costs ~$1/month)

Choose Email OTP and you'll have 2FA working in 1 hour! 🚀

