from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# --- VISTA HOME ---
@login_required
def home(request):
    context = {}
    return render(request, 'gestion/core/home.html', context)