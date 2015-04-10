from django.conf.urls import patterns, url
from transformation import views
from .views import *

urlpatterns = patterns('',
    url(r'^$', views.data_choice, name='data-choice-view'),
    url(r'csv/step/1', views.csv_upload, name='csv-upload-view'),
    url(r'csv/step/2', views.csv_column_choice, name='csv-column-choice-view'),

)
