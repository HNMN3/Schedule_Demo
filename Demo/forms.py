# Keep coding and change the world..And do not forget anything..Not Again..
from django import forms
from .models import SiteUser
import pytz


class ScheduleForm(forms.Form):
    timezone = forms.ChoiceField(choices=[(x, x) for x in pytz.common_timezones if x not in {"Australia/Eucla",
                                                                                             "Pacific/Chatham"}])
    date = forms.DateField(widget=forms.TextInput(attrs={'type': 'date'}))


class SetAvailabilityForm(forms.Form):
    timezone = forms.ChoiceField(choices=[(x, x) for x in pytz.common_timezones if x not in {"Australia/Eucla",
                                                                                             "Pacific/Chatham"}])
