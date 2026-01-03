"""
Shared Kernel: Mixins reutilizables
"""
from django.contrib.auth.mixins import UserPassesTestMixin


class OwnerRequiredMixin(UserPassesTestMixin):
    """
    Mixin para asegurar que solo el staff/owner pueda ejecutar acciones.
    
    Uso:
        class MyView(LoginRequiredMixin, OwnerRequiredMixin, View):
            pass
    
    Referencia: https://docs.djangoproject.com/en/stable/topics/auth/default/#the-userpassestestmixin-mixin
    """
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser