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

@login_required
def edit_profile(request):
    if request.method == 'POST':
        # You MUST include request.FILES
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            # Extra check: if they somehow upload a logo but aren't premium, block it
            if not request.user.is_premium:
                request.user.logo = None
            
            form.save()
            return redirect('dashboard')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'account/edit_profile.html', {'form': form})