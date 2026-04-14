from django.shortcuts import render

# Create your views here.


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from accounts.models import User
import requests
import uuid
import json
from django.conf import settings

@login_required
def create_order(request):
    order_id = f"ORDER_{uuid.uuid4().hex[:8]}"
    url = f"{settings.CASHFREE_BASE_URL}/orders"

    headers = {
        "x-client-id": settings.CASHFREE_APP_ID,
        "x-client-secret": settings.CASHFREE_SECRET,
        "x-api-version": "2023-08-01",
        "Content-Type": "application/json"
    }
    
    plan = request.GET.get("plan")
    amount = 2149 if plan == "yearly" else 249

    # Dynamic domain for Render
    domain = request.build_absolute_uri('/')[:-1]

    data = {
        "order_id": order_id,
        "order_amount": amount,
        "order_currency": "INR",
        "customer_details": {
            "customer_id": str(request.user.id),
            "customer_email": request.user.email,
            "customer_phone": getattr(request.user, 'phone', '9000000000') 
        },
        "order_meta": {
            "return_url": f"{domain}/payments/success/?user_id={request.user.id}"
        }
    }
    response = requests.post(url, json=data, headers=headers)
    res_data = response.json()

    # DEBUG: Check Render logs for this output!
    print(f"DEBUG: Cashfree Status: {response.status_code}")
    print(f"DEBUG: Cashfree Body: {res_data}")

    return JsonResponse(res_data)

  

@login_required
def payment_success(request):
    # This comes from the return_url you set in create_order
    user_id = request.GET.get("user_id") 
    
    # Optional: Fetch the user and check if they are already premium
    # This is a quick way to verify if the webhook already finished
    user = get_object_or_404(User, id=request.user.id)
    
    if user.is_premium:
        return render(request, "payments/success.html")
    
    # If they aren't premium yet (maybe webhook is slow), 
    # you could just show a "Processing" page or redirect to dashboard
    return redirect('dashboard')

from datetime import timedelta
from django.utils import timezone

@csrf_exempt
def webhook(request):
    try:
        data = json.loads(request.body)
        # Check for the event you selected in the Cashfree Dashboard
        if data.get("type") == "PAYMENT_SUCCESS_WEBHOOK":
            payment_data = data.get("data", {})
            order_details = payment_data.get("order", {})
            customer_details = payment_data.get("customer_details", {})
            
            user_id = customer_details.get("customer_id")
            amount = float(order_details.get("order_amount", 0))

            if user_id:
                user = User.objects.get(id=user_id)
                user.is_premium = True
                
                # Logic: Set expiry based on amount
                if amount >= 2000: # Yearly Plan (₹2149)
                    user.premium_expiry = timezone.now() + timedelta(days=365)
                else: # Monthly Plan (₹249)
                    user.premium_expiry = timezone.now() + timedelta(days=30)
                
                user.save()
                return JsonResponse({"status": "success"}, status=200)
                
    except Exception as e:
        print(f"Webhook Error: {e}")
        
    return JsonResponse({"status": "received"}, status=200)
