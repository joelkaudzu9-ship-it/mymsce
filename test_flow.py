# test_flow.py
"""
Manual Testing Checklist:

□ User Registration
   □ Can register with valid data
   □ Shows error for existing email
   □ Verification link appears in console

□ Email Verification
   □ Clicking link verifies email
   □ Redirects to login with success message

□ Login
   □ Can login with verified email
   □ Cannot login with wrong password
   □ "Remember Me" works

□ Pricing Page
   □ Shows all plans correctly
   ✓ Form 3: 1,030/6,695/12,500
   ✓ Form 4: 1,030/6,695/12,500
   ✓ Combined: 1,545/8,500/19,500

□ Subscription
   □ Can select a plan
   □ Redirects to payment page
   □ Shows correct amount

□ Payment (Sandbox)
   □ Can enter phone number
   □ Can select payment method
   □ Initiates payment with PayChangu
   □ Shows payment status page

□ Access Control
   □ Cannot access Form 4 lessons with Form 3 sub
   □ Can access all with Combined sub
   □ Free lessons accessible without sub

□ Admin Panel
   □ Can create subjects
   □ Can create lessons
   □ Can view users
   □ Can view payments

□ Profile
   □ Shows correct user info
   □ Shows payment history
   □ Shows subscription status
"""