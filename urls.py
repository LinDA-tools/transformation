from django.conf.urls import patterns, url
from transformation import views
from .views import *

urlpatterns = patterns('',
    url(r'^$', views.index),
    url(r'^csv/upload$', views.csv_view, name='csv-upload-view'),

)