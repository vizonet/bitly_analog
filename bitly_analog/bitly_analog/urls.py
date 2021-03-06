"""
Definition of urls for bitly_analog.
"""

from datetime import datetime
from django.urls import path
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.conf.urls import include
from app import forms, views


urlpatterns = [
    # from Django
    path('', views.home, name='home'),
    path('', include('app.urls')),
]


'''
    path('admin/', admin.site.urls),
    path('login/',
         LoginView.as_view
         (
             template_name='app/login.html',
             authentication_form=forms.BootstrapAuthenticationForm,
             extra_context=
             {
                 'title': 'Log in',
                 'year' : datetime.now().year,
             }
         ),
         name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
'''