import datetime

import pytz
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
# Create your views here.
from django.urls import reverse
from django.views.generic import TemplateView
import json
from Demo.forms import ScheduleForm, SetAvailabilityForm
from Demo.models import SiteUser, Schedule, TimeSlot, Availability


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
    # Just leveraging the Inheritance feature by defining the common data and function here
    template_name = 'Demo/sign-in.html'
    is_salesman = None

    def dispatch(self, request, *args, **kwargs):
        # Check if already user is logged in
        if request.user.is_authenticated():
            return HttpResponseRedirect('/home')
        return render(request, self.template_name, {'is_salesman': self.is_salesman})


# Below two View are for differentiating between salesman and customer
class SalesmanSignInView(BaseView):
    is_salesman = 1


class CustomerSignInView(BaseView):
    is_salesman = 0


# Logout the user
def logout(request):
    site_user = SiteUser.objects.get(user=request.user)
    auth_logout(request)
    # Then redirect to login page
    if site_user.is_salesman:
        return HttpResponseRedirect('/salesman')
    return HttpResponseRedirect('/customer')


@login_required
def schedule_demo(request):
    site_user = SiteUser.objects.get(user=request.user)

    # To provide available slots to customer the timezone and a date is required
    # If both available then just that data from availability slots
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            site_user.timezone = form.cleaned_data['timezone']
            site_user.save()
    else:
        data = {'date': datetime.datetime.now().date(),
                'timezone': site_user.timezone}
        if site_user.timezone:
            form = ScheduleForm(data)
        else:
            form = ScheduleForm()

    return render(request, 'Demo/schedule_demo.html', {'form': form})


def convert_time(hour, minute, input, output, date=None):
    '''
    This method converts a particular time into another timezone ex. UTC to Asia/Kolkata
    :return: the converted time object
    '''
    input_time_zone = pytz.timezone(input)
    output_time_zone = pytz.timezone(output)
    if date is None:
        date = datetime.datetime.now().date()
    time = datetime.time(hour, minute)
    date_time = datetime.datetime.combine(date, time)
    date_time = input_time_zone.localize(date_time)

    # convert to UTC
    utc_date_time = date_time.astimezone(output_time_zone)

    utc_time = utc_date_time.time()
    return utc_date_time


@login_required
def set_availability(request):
    site_user = SiteUser.objects.get(user=request.user)  # Getting the SiteUser instance
    delta = datetime.timedelta(minutes=30)  # Slot duration 30 minutes

    if request.method == 'POST':
        # If a post request is made then delete previous availability data of salesman
        # and update the availability of the salesman
        form = SetAvailabilityForm(request.POST)
        if form.is_valid():
            site_user.timezone = form.cleaned_data['timezone']
            site_user.save()
        availability = json.loads(request.POST['availability-array'])
        Availability.objects.filter(salesman=site_user).delete()
        utc_date_time = convert_time(0, 0, site_user.timezone, "UTC")
        for available in availability:
            if available:
                try:
                    slot = TimeSlot.objects.get(slot_time=utc_date_time.time())
                except TimeSlot.DoesNotExist:
                    slot = TimeSlot.objects.create(slot_time=utc_date_time.time())

                Availability.objects.create(salesman=site_user,
                                            slot=slot)
            utc_date_time += delta
    else:
        # In get request get the availability data of salesman from database and pass it to the frontend

        # If salesman has mentioned his/her timezone before
        data = {}
        if site_user.timezone:
            data['timezone'] = site_user.timezone
            form = SetAvailabilityForm(data)
        else:
            form = SetAvailabilityForm()

        # Get available slots
        available_slots = Availability.objects.filter(salesman=site_user).values("slot__slot_time")
        availability = []
        utc_date_time = convert_time(0, 0, site_user.timezone, "UTC")

        # for each slot check if that slot is available in available_slots of salesman
        for i in range(48):
            is_available = available_slots.filter(slot__slot_time=utc_date_time.time())
            availability.append(bool(is_available))
            utc_date_time += delta

    # return the view along with form data and availability information
    return render(request, 'Demo/set_availability.html',
                  {'form': form, 'availability': availability})
