from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UserProfileForm

def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to PaveWatch, {user.username}! Your account has been created.")
            return redirect("home")
    else:
        form = UserRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})

@login_required
def profile(request):
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile details have been updated.")
            return redirect("profile")
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})

def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")
