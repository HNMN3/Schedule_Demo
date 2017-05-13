from django.db import models


# Create your models here.

# Model for User, which may be a Salesman or a Customer
# stores the data provided by google account
class User(models.Model):
    email = models.EmailField(primary_key=True)
    name = models.CharField(max_length=50)
    img_url = models.TextField()
    # user type can be either salesman or customer so used boolean field
    is_salesman = models.BooleanField(choices=[(True, 'yes'), (False, 'no')])

    def __str__(self):
        return self.name

class Schedule(models.Model):
    sch_id = models.AutoField(primary_key=True)  # Schedule ID
    salesman = models.ForeignKey(User, on_delete=models.CASCADE, related_name='salesman')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer')
