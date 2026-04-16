from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)  # 👈 changed
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


from django.shortcuts import render, redirect
from .forms import UserProfileForm

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import UserProfileForm


@login_required
def edit_profile(request):
    user = request.user

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)

        if form.is_valid():
            updated_user = form.save(commit=False)

            # ─────────────────────────────
            # 🔒 PREMIUM GUARDS
            # ─────────────────────────────
            if not user.is_premium:
                updated_user.logo = user.logo  # don't overwrite

            # ─────────────────────────────
            # 🧠 SAFE DEFAULTS (10x UX)
            # ─────────────────────────────
            updated_user.company_name = request.POST.get('company_name', '').strip()
            updated_user.company_address = request.POST.get('company_address', '').strip()
            updated_user.gst_number = request.POST.get('gst_number', '').strip()

            # Payment link safe
            payment_link = request.POST.get('payment_link', '').strip()
            if payment_link.startswith("http"):
                updated_user.payment_link = payment_link

            # Tax safe
            try:
                tax = float(request.POST.get('default_tax', 0))
                updated_user.default_tax = max(tax, 0)
            except:
                updated_user.default_tax = 0

            # Due days safe
            try:
                days = int(request.POST.get('due_days', 7))
                updated_user.due_days = max(days, 1)
            except:
                updated_user.due_days = 7

            # Currency safe
            updated_user.currency = request.POST.get('currency', '₹')[:5]

            updated_user.save()

            return redirect('dashboard')

    else:
        form = UserProfileForm(instance=user)

    return render(request, 'account/edit_profile.html', {
        'form': form
    })
