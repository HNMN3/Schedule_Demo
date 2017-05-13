from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
from Demo.models import User, Schedule


def home(request):
    if request.method == "POST":
        print(request.POST['email'])
        # if someone tries to open directly this page
        try:
            user = User.objects.get(email=request.POST['email'])
        except User.DoesNotExist:
            data = {key: request.POST[key] for key in request.POST}
            data.pop('csrfmiddlewaretoken')
            data['is_salesman'] = True
            user = User.objects.create(**data)
            user.save()
        schedules = None
        if user.is_salesman:
            schedules = Schedule.objects.filter(salesman=user)
        else:
            schedules = Schedule.objects.filter(customer=user)
        return render(request, 'Demo/home.html', {'user': user, 'schedules': schedules})
    return HttpResponse("You are not allowed to access this page directly!!")
