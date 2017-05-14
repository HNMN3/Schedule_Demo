from django.contrib.auth.models import User
from django.db import models


# Create your models here.

# Model for User, which may be a Salesman or a Customer
# stores the data provided by google account
class SiteUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Using Django default model for authentication
    name = models.CharField(max_length=50)
    img_url = models.TextField()
    # user type can be either salesman or customer so used boolean field
    is_salesman = models.BooleanField(choices=[(True, 'yes'), (False, 'no')])
    timezone = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name


class Schedule(models.Model):
    sch_id = models.AutoField(primary_key=True)  # Schedule ID
    salesman = models.ForeignKey(SiteUser, on_delete=models.CASCADE, related_name='salesman')
    customer = models.ForeignKey(SiteUser, on_delete=models.CASCADE, related_name='customer')
    schedule_time = models.DateTimeField()


class TimeSlot(models.Model):
    slot_id = models.AutoField(primary_key=True)
    slot_time = models.TimeField()


class Availability(models.Model):
    salesman = models.ForeignKey(SiteUser, on_delete=models.CASCADE)
    slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)


class DemoCount(models.Model):
    salesman = models.ForeignKey(SiteUser, on_delete=models.CASCADE)
    date = models.DateField()
    job_count = models.IntegerField(default=0)
