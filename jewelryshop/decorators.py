from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden

def normal_user_required(view_func):

    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return HttpResponseForbidden("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def superuser_required(view_func):

    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
