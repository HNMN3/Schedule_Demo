from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
# Create your views here.
from django.urls import reverse
from django.views.generic import TemplateView

from Demo.models import SiteUser, Schedule


def login(request, is_salesman):
    if request.method == "POST":
        # if someone tries to open directly this page
        try:
            user = User.objects.get(email=request.POST['email'])
        except User.DoesNotExist:
            # copy request.POST into data
            data = {key: request.POST[key] for key in request.POST}

            # create django auth user model instance
            email = data.pop('email')
            user = User(username=email[:email.index('@')], email=email)
            user.set_password(data.pop('password'))
            user.save()

            # removing unnecessary data
            data.pop('csrfmiddlewaretoken')

            # Adding required data to crete SiteUser instance
            data['is_salesman'] = is_salesman == "1"
            data['user'] = user

            # create SiteUser instance
            SiteUser.objects.create(**data)

        # Authenticate the user
        username = user.username
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        auth_login(request, user)
        return HttpResponseRedirect('/home')

    return HttpResponse("You are not allowed to access this page directly!!")


@login_required
def home(request):
    user = SiteUser.objects.get(user=request.user)
    return render(request, 'Demo/home.html', {'user': user})


class BaseView(TemplateView):
    template_name = 'Demo/sign-in.html'

    def dispatch(self, request, *args, **kwargs):
        # Check if already user is logged in
        if request.user.is_authenticated():
            return HttpResponseRedirect('/home')
        return render(request, self.template_name)


class SalesmanSignInView(BaseView):
    def get_context_data(self, **kwargs):
        return {'is_salesman': 1}


class CustomerSignInView(BaseView):
    def get_context_data(self, **kwargs):
        return {'is_salesman': 0}


def logout(request):
    site_user = SiteUser.objects.get(user=request.user)
    auth_logout(request)
    if site_user.is_salesman:
        return HttpResponseRedirect('/salesman')
    return HttpResponseRedirect('/customer')
