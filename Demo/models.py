from django.db import models
from django.contrib.auth.models import User


# Create your models here.

# Model for User, which may be a Salesman or a Customer
# stores the data provided by google account
class SiteUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Using Django default model for authentication
    name = models.CharField(max_length=50)
    img_url = models.TextField()
    # user type can be either salesman or customer so used boolean field
    is_salesman = models.BooleanField(choices=[(True, 'yes'), (False, 'no')])

    def __str__(self):
        return self.name


class Schedule(models.Model):
    sch_id = models.AutoField(primary_key=True)  # Schedule ID
    salesman = models.ForeignKey(SiteUser, on_delete=models.CASCADE, related_name='salesman')
    customer = models.ForeignKey(SiteUser, on_delete=models.CASCADE, related_name='customer')
