from django.conf.urls import patterns, url
from transformation import views
from .views import *

urlpatterns = patterns('',
    url(r'^index.html$', views.index, name='transformation-index'),
    url(r'^csv/upload$', views.csv_upload, name='csv-upload-view'),

)
