"""myproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from interactiveMap import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('map/', views.InteractiveMap.as_view(), name='map'),
    path('analysis/', views.getting_started, name='analysis_page'),
    path('analysis/timeseries/', views.timeseries, name='timeseries'),
    path('analysis/interpolation/', views.interpolation, name='interpolation'),
    path('analysis/animation/', views.animation, name='animation'),
    path('analysis/clusterization/', views.clusterization, name='clusterization'),
]
