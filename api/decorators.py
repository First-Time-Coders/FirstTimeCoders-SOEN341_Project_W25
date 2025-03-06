from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from datetime import datetime

SUPABASE_URL = "https://rsdvkupcprtchpzuxgtd.supabase.co"

def supabase_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        print("decorator called")
        # Check if the user is logged in
        if not request.session.get('user_uuid'):
            messages.error(request, "You must be logged in to access this page.")
            return redirect('login')

        # Add cache-control headers to prevent caching
        response = view_func(request, *args, **kwargs)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    return _wrapped_view
