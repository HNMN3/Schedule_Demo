"""Schedule_Demo URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.views.generic import TemplateView
from Demo import views

# list of urls
urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^customer', views.CustomerSignInView.as_view(), name='customer_login'),
    url(r'^salesman', views.SalesmanSignInView.as_view(), name='salesman_login'),
    url(r'^login/([0-1])', views.login, name='login'),
    url(r'^login', TemplateView.as_view(template_name='Demo/login_redirect.html'), name='login-redirect'),
    url(r'^logout', views.logout, name='logout'),
    url(r'^home', views.home, name='home'),
    url(r'^schedule-demo', views.schedule_demo, name='schedule-demo'),
    url(r'^get-available-slots', views.get_available_slots, name='get-available-slots'),
    url(r'^set-availability', views.set_availability, name='set-availability'),
    url(r'^save-credentials', views.oauth2redirect, name='save-credentials'),
    url(r'^add-to-calendar', views.add_to_google_calender, name='add-to-calendar')
]
