# Create your views here.
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator 
from django.views.decorators.http import require_POST

from accounts.services.fast2sms import send_otp
from accounts.models import OTPverification

import logging
import hashlib

from django.utils import timezone
from datetime import timedelta

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
User = get_user_model()

class SessionRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if "user" not in request.session:
            return redirect('register')   # 🔥 your entry page
        return super().dispatch(request, *args, **kwargs)

class VerifyView(View):
    template_name = "home/auth.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        full_name = request.POST.get("full_name")
        username = request.POST.get("username")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, self.template_name)

        if User.objects.filter(phone=phone).exists():
            messages.info(request, "Phone number already registered")
            request.session["user"] = {'user_phone':phone,
                                       'full_name':full_name,
                                       'username':username}
            try:
                return twilio_service(request)
            except Exception as e:
                messages.error(request,"Oops! We encountered a problem. Try again later.")
                logging.error(f"User couldn't login! {str(e)}")
                return redirect('register')
            
        request.session["user"] = {'user_phone':phone,
                            'full_name':full_name,
                            'username':username}
        
        try:
            return twilio_service(request)
        except Exception as e:
            messages.error(request,"Oops! We encountered a problem. Try again later.")
            logging.error(f"User couldn't login! {str(e)}")
            return redirect('register')

class VerifyOtp(SessionRequiredMixin,View):
    template_name = "home/verify_otp.html"

    def get(self, request, *args, **kwargs):
        phone=request.session['user']['user_phone']
        
        context = {
            "masked_phone": "x" * (len(phone) - 3) + phone[-3:],
        }
        
        return render(request, self.template_name, context)
    
    def post(self,request,*args,**kwargs):
        username=request.session['user']['username']
        fullname=request.session['user']['full_name']
        phone=request.session['user']['user_phone']        
        otp=request.POST.get('otp')
        
        otp_record=OTPverification.objects.filter(phone=phone).first()
        if otp_record:
            hashed_otp=hashlib.sha256(otp.encode()).hexdigest()
            
            if otp_record.otp_hash == hashed_otp:
                messages.success(request,'Welcome, have a nice chat !!')
                otp_record.otp_hash=None
                otp_record.attempt_count=0
                otp_record.resend_count=0
                otp_record.save()
                try:
                    user,status=User.objects.get_or_create(phone=phone)                    
                except Exception as e:
                    messages.error(request,message='Couldnt create your profile. Please try again later')
                    logging.error(msg=f'User couldnt be registered because, {str(e)}')
                    return redirect('register')
                return redirect('entry_profile')   
            else:
                if otp_record.attempt_count < 3:
                    messages.error(request,message=f'Hmmmm, Wrong OTP! You have {otp_record.attempt_count} chances left.')
                    otp_record.attempt_count = (otp_record.attempt_count or 0) + 1
                    otp_record.save()
                    return redirect('verify_otp')
                else:
                    messages.error(request,message="You've exhausted your attempts.")
                    logging.error(msg=f'You\'ve exhausted your attempts.')
                    return redirect('verify_otp')
            
class EntryDetails(SessionRequiredMixin,View):
    template_name='home/profile/entry_profile.html'
    def get(self,request,*args,**kwargs):
        phone=request.session['user']['user_phone']
        
        user=User.objects.filter(phone=phone).first()
        
        context={
            'user':user
        }
        
        return render(request,self.template_name,context)
    
    def post(self,request,*args,**kwargs):
        phone=request.session['user']['user_phone']
        user=User.objects.filter(phone=phone).first()
        
        if user:
            photo=request.FILES.get('profile_photo')
            display_name=request.POST.get('display_name')
            
            user.profile_picture=photo
            user.username=display_name
            user.save()
            login(request,user)
            
            return redirect('dashboard')
        else:
            return redirect('register')
@require_POST
@login_required(redirect_field_name='register')
def logout_function(request):
    if not request.user.is_authenticated:
        return redirect('regster') 
    logout(request)
    return redirect('register')

def twilio_service(request):
    try:
        now = timezone.now()
        phone=request.session['user']['user_phone']
        
        #Creating a otp instance or fetching a otp instance
        user_otp,created=OTPverification.objects.get_or_create(phone=phone)
        
        #If fetched then check if the previously sent otp is 30s older or not.
        if not created:
            if user_otp.created_at > now - timedelta(seconds=30):
                messages.error(request,"Please wait before requesting another OTP")
                return redirect('verify_otp')
            if user_otp.resend_count >= 4:
                messages.error(request,"You have exhausted your otp resend's for the day. Please come back after 24 hours.")
                return redirect('register')
            
        #If the above check passes, send a new otp
        code=send_otp(phone)
        
        #If the otp returns none, check the logs and identify the issue why the otp wasn't sent.
        if code == 'None':
            messages.error(request,message='Please try again later')
            return redirect('register')
        
        #If the otp returns the encrypted code, then move forward and save it in the db.
        user_otp.otp_hash=code
        user_otp.created_at = timezone.now()
        user_otp.resend_count = (user_otp.resend_count or 0) + 1
        user_otp.save()
        messages.info(request,'Otp Sent Successfully')
        return redirect('verify_otp')
    
    #Catch the errors efficiently in the above process.
    except Exception as e:
        messages.error(request,'We Encountered an Error. Please try again later.')
        logging.error(msg=f'Problem sending OTP, {str(e)}')
        return redirect('verify_otp')
            
