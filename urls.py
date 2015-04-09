from django.conf.urls import patterns, url
from transformation import views
from .views import *

urlpatterns = patterns('',
    url(r'index.html$', views.index, name='transformation-index'),
    url(r'datachoice', views.data_choice, name='data-choice-view'),
    url(r'csv/upload', views.csv_upload, name='csv-upload-view'),
    url(r'csv/columnchoice', views.csv_column_choice, name='csv-column-choice-view'),

)
