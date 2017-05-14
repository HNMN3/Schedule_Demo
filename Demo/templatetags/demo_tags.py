# Keep coding and change the world..And do not forget anything..Not Again..
from django import template
import pytz
import datetime

register = template.Library()


# This tag is used to show the event time according to the timezone of customer or salesman
@register.simple_tag
def convert_time(schedule, user, flag):
    timezone = user.timezone
    input_time_zone = pytz.utc
    output_time_zone = pytz.timezone(timezone)
    date = schedule.schedule_date_time.date()
    time = datetime.time(schedule.schedule_date_time.hour, schedule.schedule_date_time.minute)
    date_time = datetime.datetime.combine(date, time)
    date_time = input_time_zone.localize(date_time)

    # convert to UTC
    utc_date_time = date_time.astimezone(output_time_zone)
    if flag == 0:
        return utc_date_time.date()
    return utc_date_time.time()
