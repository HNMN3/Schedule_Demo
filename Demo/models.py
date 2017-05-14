import datetime
import pytz
from django import template
from django.contrib.auth.models import User
from django.db import models
from oauth2client.contrib.django_util.models import CredentialsField


# Create your models here.

# Model for User, which may be a Salesman or a Customer
# stores the data provided by google account
class SiteUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Using Django default model for authentication
    credential = CredentialsField()
    name = models.CharField(max_length=50)
    img_url = models.TextField()
    # user type can be either salesman or customer so used boolean field
    is_salesman = models.BooleanField(choices=[(True, 'yes'), (False, 'no')])
    timezone = models.CharField(max_length=50, default="UTC")

    def __str__(self):
        return self.name


# This model stores all the Demo Schedules
class Schedule(models.Model):
    sch_id = models.AutoField(primary_key=True)  # Schedule ID
    salesman = models.ForeignKey(SiteUser, on_delete=models.CASCADE, related_name='salesman')
    customer = models.ForeignKey(SiteUser, on_delete=models.CASCADE, related_name='customer')
    schedule_date_time = models.DateTimeField()
    event_link = models.URLField(blank=True, null=True)


# Different Time Slots of UTC, demo duration is 30 minutes so there can be 48 time slots
class TimeSlot(models.Model):
    slot_id = models.AutoField(primary_key=True)
    slot_time = models.TimeField()


# It track the all sales available at a particular time slot
class Availability(models.Model):
    salesman = models.ForeignKey(SiteUser, on_delete=models.CASCADE)
    slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)


# It keeps track of how many demo a salesman got on particular date
# so it is used to provide a round robin schedule among various salesman
class DemoCount(models.Model):
    salesman = models.ForeignKey(SiteUser, on_delete=models.CASCADE)
    date = models.DateField()
    demo_count = models.IntegerField(default=0)
