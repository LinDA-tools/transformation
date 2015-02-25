from django.conf.urls import patterns, url
from transformation import views
from .views import *

urlpatterns = patterns('',
    #url(r'^', include(router.urls)),
    url(r'^csv/upload$', views.csv_view.as_view(), name='csv-upload-view'),
)