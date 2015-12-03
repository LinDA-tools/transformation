from django.conf.urls import patterns, url

from django.views.generic.base import RedirectView

from transformation import views


urlpatterns = patterns('',
                       url(r'^$', views.data_choice, name='data-choice-view'),
                       url(r'csv/step/1', views.csv_upload, name='csv-upload-view'),
                       url(r'csv/step/2', views.csv_column_choice, name='csv-column-choice-view'),
                       url(r'csv/step/3', views.csv_subject, name='csv-subject-view'),
                       url(r'csv/step/4', views.csv_predicate, name='csv-predicate-view'),
                       url(r'csv/step/5', views.csv_object, name='csv-object-view'),
                       url(r'csv/step/6', views.csv_enrich, name='csv-enrich-view'),
                       url(r'csv/step/7', views.csv_publish, name='csv-publish-view'),
                       url(r'^status/', 'transformation.views.status', name="status"),
                       url(r'rdb/step/1',           views.rdb_select,           name='rdb-select-view'),
                       url(r'rdb/step/2',           views.rdb_sql_select,       name='rdb-sql-select-view'),
                       url(r'rdb/step/3',           views.rdb_column_choice,    name='rdb-column-choice-view'),
                       url(r'rdb/step/4',           views.rdb_subject,          name='rdb-subject-view'),
                       url(r'rdb/step/5',           views.rdb_predicate,        name='rdb-predicate-view'),
                       url(r'rdb/step/6',           views.rdb_object,           name='rdb-object-view'),
                       url(r'rdb/step/7',           views.rdb_enrich,           name='rdb-enrich-view'),
                       url(r'rdb/step/8',           views.rdb_publish,          name='rdb-publish-view'),
                       url(r'rdb/get_sql_table',    views.rdb_get_sql_table,    name='rdb-get-sql-table-view'),
                       url(r'rdb/save_mapping',     views.rdb_save_mapping,     name='rdb-save-mapping-view'),
                       url(r'rdb/get_table_values', views.rdb_get_table_values, name='rdb-get-table-values'),
#                       url(r'^lookup/(?P<queryClass>\w+)/(?P<queryString>\w+)/', 'transformation.views.lookup', name="lookup"),

)
