from django.shortcuts import redirect

class TrialCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                client = request.user.client
                if not client.is_active or client.trial_expired():
                    return redirect('trial_expired')
            except:
                pass
        return self.get_response(request)
