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
    return JsonResponse(response.json())

@login_required
def payment_success(request):
    user_id = request.GET.get("user_id")
    
    # Security: Ensure the person clicking success is actually the user being upgraded
    if str(request.user.id) != str(user_id):
        return redirect('dashboard')

    if user_id:
        user = get_object_or_404(User, id=user_id)
        user.is_premium = True
        user.save()

    return render(request, "payments/success.html")

@csrf_exempt
def webhook(request):
    # Webhooks are the "SaaS standard" for reliability
    try:
        data = json.loads(request.body)
        if data.get("type") == "PAYMENT_SUCCESS_WEBHOOK":
            user_id = data["data"]["customer_details"]["customer_id"]
            user = User.objects.get(id=user_id)
            user.is_premium = True
            user.save()
    except Exception as e:
        print(f"Webhook Error: {e}")
        
    return JsonResponse({"status": "received"})
