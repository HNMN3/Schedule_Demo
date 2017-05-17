import datetime

import pickle
import pytz
import requests
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
# Create your views here.
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
import json

from dateutil.parser import parse
from googleapiclient.discovery import build
from oauth2client import client
from oauth2client.client import OAuth2WebServerFlow, flow_from_clientsecrets

from Demo.forms import ScheduleForm, SetAvailabilityForm
from Demo.models import SiteUser, Schedule, TimeSlot, Availability, DemoCount, EventFromOtherSources
import httplib2
from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseRedirect)
from django.shortcuts import redirect
from oauth2client.contrib import xsrfutil
from oauth2client.contrib.django_util.storage import DjangoORMStorage as Storage


# All time instances are converted to UTC timezone before performing any task so that all timezone can be compared


class BaseView(TemplateView):
    # Just leveraging the Inheritance feature by defining the common data and function here
    template_name = 'Demo/sign-in.html'
    is_salesman = None

    def dispatch(self, request, *args, **kwargs):
        # Check if already user is logged in then directly go to home
        if request.user.is_authenticated():
            return HttpResponseRedirect('/home')
        return render(request, self.template_name, {'is_salesman': self.is_salesman})


# Below two View are for differentiating between salesman and customer
class SalesmanSignInView(BaseView):
    is_salesman = 1  # SignIn view for salesman


class CustomerSignInView(BaseView):
    is_salesman = 0  # SignIn view for customer


# This method logs in the request and also creates the User account if it's the very first time user logging in
def login(request, is_salesman):
    if request.method == "POST":
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
            data.pop('csrfmiddlewaretoken', 0)
            data.pop('img_url', 0)
            # Adding required data to crete SiteUser instance
            data['is_salesman'] = is_salesman == "1"
            data['user'] = user

            # create SiteUser instance
            SiteUser.objects.create(**data)

        # Authenticate the request i.e. log it in
        username = user.username
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        auth_login(request, user)
        return HttpResponseRedirect('/get-calendar-permission')

    return HttpResponse("You are not allowed to access this page directly!!")


@login_required
def home(request):
    site_user = SiteUser.objects.get(user=request.user)  # site user instance
    current_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

    # Get all the schedules of user
    if site_user.is_salesman:
        schedules = Schedule.objects.filter(salesman=site_user)
    else:
        schedules = Schedule.objects.filter(customer=site_user)

    # Now filter only those which are to be held
    schedules = schedules.filter(schedule_date_time__gte=current_time)

    # Sort the Schedules by schedule date time
    schedules = schedules.order_by('schedule_date_time')

    # return the data
    return render(request, 'Demo/home.html', {'user': site_user,
                                              'schedules': schedules})


def logout(request):
    # Logout the request
    site_user = SiteUser.objects.get(user=request.user)
    auth_logout(request)

    # Then redirect to login page
    if site_user.is_salesman:
        return HttpResponseRedirect('/salesman')
    return HttpResponseRedirect('/customer')


def any_salesman_available(on_this_date_time):
    # In this function I am first getting salesman who provided their availability on this time slot
    # and then I am removing them who are scheduled
    start_time = on_this_date_time
    end_time = on_this_date_time + datetime.timedelta(minutes=30)
    salesman_on_this_slot = Availability.objects.filter(slot__slot_time=on_this_date_time.time()).values('salesman')
    booked_salesman = EventFromOtherSources.objects.filter(
        (Q(start_time__lte=start_time) & Q(end_time__gt=start_time)) |
        (Q(start_time__lt=end_time) & Q(end_time__gte=end_time))
    ).values('salesman')

    available_salesman = []
    for salesman in salesman_on_this_slot:
        if salesman not in booked_salesman:
            available_salesman.append(salesman)

    return available_salesman


@login_required
def get_available_slots(request):
    site_user = SiteUser.objects.get(user=request.user)
    # To provide available slots to customer the timezone and a date is required
    # If both available then send data from availability slots accordingly
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        # save if customer changed his/her timezone
        if form.is_valid():
            site_user.timezone = form.cleaned_data['timezone']
            site_user.save()
        utc_date_time = convert_time(0, 0, site_user.timezone, "UTC", form.cleaned_data['date'])
    else:
        data = {'date': datetime.datetime.now().date(),
                'timezone': site_user.timezone}
        form = ScheduleForm(data)
        utc_date_time = convert_time(0, 0, site_user.timezone, "UTC", datetime.datetime.now().date())

    # Loop through all the 48 time slots of a day and check if atleast one salesman is available on that
    delta = datetime.timedelta(minutes=30)  # Duration of demo
    availability = []
    current_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    for i in range(48):
        available_salesman = []
        if utc_date_time >= current_time:
            available_salesman = any_salesman_available(utc_date_time)
        availability.append(bool(available_salesman))
        utc_date_time += delta

    return render(request, 'Demo/schedule_demo.html', {'form': form, 'availability': availability})


def get_salesman_demo_count(salesman_pk, date):
    # To get the number of how many demo are scheduled with the given salesman on given date
    salesman = SiteUser.objects.get(pk=salesman_pk['salesman'])

    # Creates the one if not exist
    try:
        demo_count = DemoCount.objects.get(salesman=salesman, date=date)
    except DemoCount.DoesNotExist:
        demo_count = DemoCount.objects.create(salesman=salesman, date=date)

    return demo_count


@login_required
def schedule_demo(request):
    global flow
    site_user = SiteUser.objects.get(user=request.user)
    if request.method == "POST":
        # Here user has selected a date and time slot
        date = datetime.datetime.strptime(request.POST['date'], '%Y-%m-%d')
        index = int(request.POST['index'])
        hour = int(index / 2)
        minute = 30 * (index % 2)
        utc_datetime = convert_time(hour, minute, site_user.timezone, "UTC", date.date())

        # get all the salesman available on that time slot
        available_salesman = any_salesman_available(utc_datetime)

        # get demo counts of all available salesmen
        demo_counts = [get_salesman_demo_count(salesman, utc_datetime.date()) for salesman in available_salesman]

        # Schedule the demo with the one who has the lowest number of Demo scheduled
        salesman_with_min_demo_count = min(demo_counts, key=lambda x: x.demo_count)
        salesman_with_min_demo_count.demo_count += 1
        salesman_with_min_demo_count.save()
        s = Schedule.objects.create(customer=site_user, salesman=salesman_with_min_demo_count.salesman,
                                    schedule_date_time=utc_datetime)

        # Now redirect to view which inserts this schedule into calender
        request.session['sch_id'] = s.sch_id
        return HttpResponseRedirect('/add-to-calendar')

    # Allows only post request
    return HttpResponse("OOPS!! Nothing is here please goto homepage!!")


def convert_time(hour, minute, input_timezone, output_timezone, date=None):
    '''
    This method converts a particular time into another timezone ex. UTC to Asia/Kolkata
    :return: the converted time object
    '''
    input_time_zone = pytz.timezone(input_timezone)
    output_time_zone = pytz.timezone(output_timezone)
    if date is None:
        date = datetime.datetime.now().date()
    time = datetime.time(hour, minute)
    date_time = datetime.datetime.combine(date, time)
    date_time = input_time_zone.localize(date_time)

    # convert to UTC

    utc_date_time = date_time.astimezone(output_time_zone)

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

        # Parse the availability array given by user
        availability = json.loads(request.POST['availability-array'])
        Availability.objects.filter(salesman=site_user).delete()
        utc_date_time = convert_time(0, 0, site_user.timezone, "UTC")

        # Insert Availability data into Database
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


# flow created from client secrets file
flow = client.flow_from_clientsecrets(
    settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
    scope=settings.GOOGLE_SCOPE,
    redirect_uri=settings.OAUTH_REDIRECT_URI)
flow.params['access_type'] = 'offline'  # offline access


# flow.params['include_granted_scopes'] = True  # incremental auth


@login_required
def oauth2redirect(request):
    global flow
    # It is called after user allows the calender permission
    # stores the credentials and redirects to next
    credential = flow.step2_exchange(request.GET['code'])
    storage = Storage(SiteUser, 'user', request.user, 'credential')
    storage.put(credential)
    return HttpResponseRedirect(request.session.pop('redirect_url'))


@login_required
def add_to_google_calender(request):
    site_user = SiteUser.objects.get(user=request.user)

    # Get Credentials
    storage = Storage(SiteUser, 'user', request.user, 'credential')
    credential = storage.get()

    # Validate them if invalid then authorize the request again
    if credential is None or credential.invalid:
        auth_uri = flow.step1_get_authorize_url()
        request.session['redirect_url'] = '/add-to-calendar'
        return HttpResponseRedirect(auth_uri)

    # Get the service
    http = httplib2.Http()
    http_authorized = credential.authorize(http)
    service = build("calendar", "v3", http=http_authorized)
    schedule = Schedule.objects.get(sch_id=request.session.pop('sch_id'))

    # Event to be added
    event = {
        'summary': 'Demo Scheduled for Scribe',
        'location': 'Skype',
        'description': 'To get to know about the service and products of Scribe.',
        'start': {
            'dateTime': schedule.schedule_date_time.isoformat(),
        },
        'end': {
            'dateTime': (schedule.schedule_date_time + datetime.timedelta(minutes=30)).isoformat(),
        },
        'attendees': [
            {'email': schedule.customer.user.email},
            {'email': schedule.salesman.user.email},
        ],
    }

    # Insert the Event
    event = service.events().insert(calendarId='primary', body=event).execute()
    schedule.event_link = event.get('htmlLink')

    # Redirect to homepage
    return HttpResponseRedirect('/home')


@login_required
def test(request):
    site_user = SiteUser.objects.get(user=request.user)
    storage = Storage(SiteUser, 'user', request.user, 'credential')
    credential = storage.get()
    if credential is None or credential.invalid:
        auth_uri = flow.step1_get_authorize_url()
        request.session['redirect_url'] = '/test'
        return HttpResponseRedirect(auth_uri)
    print(credential.get_access_token().access_token)
    return HttpResponse('<br>'.join(dir(credential.get_access_token())))


@login_required
def get_calendar_permission(request):
    site_user = SiteUser.objects.get(user=request.user)
    storage = Storage(SiteUser, 'user', request.user, 'credential')
    credential = storage.get()
    if credential is None or credential.invalid \
            or credential.id_token['email'] != site_user.user.email:
        auth_uri = flow.step1_get_authorize_url()
        request.session['redirect_url'] = '/get-calendar-permission'
        return HttpResponseRedirect(auth_uri)

    if site_user.is_salesman and not site_user.notification_enabled:
        # Get the service
        http = httplib2.Http()
        http_authorized = credential.authorize(http)
        service = build("calendar", "v3", http=http_authorized)
        next_page_token = None
        while True:
            event_request = service.events().list(
                calendarId='primary',
                singleEvents=True,
                orderBy='startTime',
                maxResults=10,
                pageToken=next_page_token
            )
            event_results = event_request.execute()
            events = event_results.get('items', [])
            for event in events:
                try:
                    event_model = EventFromOtherSources.objects.get(event_id=event['id'])
                except EventFromOtherSources.DoesNotExist:
                    start_time = parse(event['start']['dateTime'])
                    end_time = parse(event['end']['dateTime'])
                    event_model = EventFromOtherSources.objects.create(
                        event_id=event['id'],
                        salesman=site_user,
                        start_time=start_time - start_time.utcoffset(),
                        end_time=end_time - end_time.utcoffset()
                    )
            next_page_token = event_results.get('nextPageToken')

            if next_page_token is None:
                break

        email = site_user.user.email
        url = 'https://www.googleapis.com/calendar/v3/calendars/{email}/events/watch'.format(email=email)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + credential.get_access_token().access_token
        }
        data = {
            'id': 'notification-channel-id-for-' + email[:email.index('@')].replace('.', '-'),
            "type": "web_hook",
            "address": "https://cdf1fd5c.ngrok.io/notifications"
        }
        res = requests.post(url, data=json.dumps(data), headers=headers)
        site_user.notification_channel_id = data['id']
        site_user.notification_enabled = True
        site_user.save()

    return HttpResponseRedirect('/home')


@csrf_exempt
def notifications(request):
    channel_id = request.META['HTTP_X_GOOG_CHANNEL_ID']
    try:
        site_user = SiteUser.objects.get(notification_channel_id=channel_id)
    except SiteUser.DoesNotExist:
        print('Error')
        print(request.META)
        return HttpResponse(status=200)
    storage = Storage(SiteUser, 'user', site_user.user, 'credential')
    credential = storage.get()

    # Get the service
    http = httplib2.Http()
    http_authorized = credential.authorize(http)
    service = build("calendar", "v3", http=http_authorized)
    next_page_token = None
    while True:
        event_request = service.events().list(
            calendarId='primary',
            singleEvents=True,
            orderBy='startTime',
            maxResults=10,
            pageToken=next_page_token
        )
        event_results = event_request.execute()
        events = event_results.get('items', [])
        for event in events:
            try:
                event_model = EventFromOtherSources.objects.get(event_id=event['id'])
            except EventFromOtherSources.DoesNotExist:
                start_time = parse(event['start']['dateTime'])
                end_time = parse(event['end']['dateTime'])
                event_model = EventFromOtherSources.objects.create(
                    event_id=event['id'],
                    salesman=site_user,
                    start_time=start_time - start_time.utcoffset(),
                    end_time=end_time - end_time.utcoffset()
                )
        next_page_token = event_results.get('nextPageToken')

        if next_page_token is None:
            break

    return HttpResponse(status=200)
