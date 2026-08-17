from django.contrib import admin
from .models import CustomUser, OTPRecord

admin.site.register(CustomUser)
admin.site.register(OTPRecord)
