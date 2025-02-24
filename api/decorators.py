from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def supabase_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('user_uuid'):
            messages.error(request, "You must be logged in to access this page.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
