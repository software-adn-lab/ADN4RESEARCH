from django.contrib.auth import get_user_model

User = get_user_model()

class DevUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si el usuario no está autenticado, le asignamos el superusuario con ID=1
        if not request.user.is_authenticated:
            try:
                request.user = User.objects.get(id=1)
            except User.DoesNotExist:
                # Maneja el caso en que el usuario con ID=1 no exista
                pass
        
        response = self.get_response(request)
        return response