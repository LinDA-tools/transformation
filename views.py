import csv
from io import TextIOWrapper
from io import StringIO
import os
import json
from django.http import HttpResponse
from django.shortcuts import render, render_to_response, redirect
from django.template import RequestContext
import pandas as pd
from django.http import JsonResponse
import requests
from django.core.files.base import ContentFile
from .forms import *
from .settings import API_HOST
from transformation.models import Mapping
import copy
import datetime
from itertools import chain  # for concatenating ranges
import re
import time
from django.contrib.sessions.models import Session
from django.utils import timezone
import shutil
import logging

# ###############################################
#########       RDB                    ##########
# ###############################################
import MySQLdb as mdb
from MySQLdb.constants import FIELD_TYPE, FLAG
import sys
import re
import numpy as np
from django.utils.http import urlquote
from urllib import parse
from transformation.models import DbMapping
from django.http import QueryDict
import ast
# ###############################################
#########       END RDB                ##########
# ###############################################


logger = logging.getLogger(__name__)

# ###############################################
# MODELS
# ###############################################

def data_choice(request):
    logger.info("VIEW data_choice")
    request.session['processing_status'] = get_status_dict("data_choice")
    # logger.info(request.session)
    if 'csv_rows' in request.session:
        del request.session['csv_rows']
    if 'csv_raw' in request.session:
        del request.session['csv_raw']
    if 'csv_dialect' in request.session:
        del request.session['csv_dialect']
    if 'file_name' in request.session:
        del request.session['file_name']
    if 'model' in request.session:
        del request.session['model']
    if 'rdf_array' in request.session:
        del request.session['rdf_array']
    if 'rdf_prefix' in request.session:
        del request.session['rdf_prefix']
    if 'processing_status' in request.session:
        request.session['processing_status'] = "data_choice"
    # ###############################################
    #########       RDB                    ##########
    # ###############################################
    if 'model' in request.session:
        del request.session['model']
    if 'fkeys' in request.session:
        del request.session['fkeys']
    if 'db' in request.session:
        del request.session['db']
    if 'db_databasetype' in request.session:
        del request.session['db_databasetype']
    if 'db_host' in request.session:
        del request.session['db_host']
    if 'db_user' in request.session:
        del request.session['db_user']
    if 'db_password' in request.session:
        del request.session['db_password']
    db_mappings = DbMapping.objects.filter(user=request.user.id)

    delete_unused_tmp_files()

    form = DataChoiceForm()
    mappings = Mapping.objects.filter(user=request.user.id)
#    return render_to_response('transformation/data_choice.html', {'form': form, 'mappings': mappings},
#                              context_instance=RequestContext(request))
    return render_to_response('transformation/data_choice.html', {'form': form, 'mappings': mappings, 'db_mappings': db_mappings}, context_instance=RequestContext(request))


def csv_upload(request):
    logger.info("VIEW csv_upload")
    # save file

    form_action = 2
    publish_message = ""

    request.session['processing_status'] = get_status_dict("csv_upload")

    if request.method == 'POST':
        logger.debug("PATH 1 - POST")
        # a raw representation of the CSV file is also kept as we want to be able to change the CSV dialect and then reload the page
        csv_raw = None
        csv_rows = None
        csv_dialect = None
        upload_file_name = 'no file selected'

        # when an upload file was selected in html form, APPLY BUTTON
        if not request.FILES:
            form = UploadFileForm(request.POST)
            if request.POST and form.is_valid() and form is not None:
                logger.debug("PATH 1.1 - no file uploaded")
                # content is passed on via hidden html input fields
                if 'save_path' in request.session:
                    csv_rows, csv_dialect = process_csv(open(request.session['save_path'], "r"), form)
                else:
                    logger.debug('no raw csv')

                upload_file_name = form.cleaned_data['hidden_filename_field']

            # if page is loaded without POST
            else:
                logger.debug("PATH 1.2")

        # when file was uploaded
        else:  # if request.FILES:
            logger.debug("PATH 3 - file was uploaded")

            form = UploadFileForm(request.POST, request.FILES)
            upload_file_name = request.FILES['upload_file'].name
            upload_file = request.FILES['upload_file'].file

            logger.info('File: %s', upload_file_name)

            # transformation of excel files to csv
            if upload_file_name[-4:] == "xlsx" or upload_file_name[-4:] == ".xls":
                # logger.info(upload_file_name[-4:]);
                data_xls = pd.read_excel(request.FILES['upload_file'], 0, index_col=0)
                if not os.path.exists('tmp'):
                    os.makedirs('tmp')
                data_xls.to_csv('tmp/' + upload_file_name[:-4] + '.csv', encoding='utf-8')
                upload_file = open('tmp/' + upload_file_name[:-4] + '.csv', "rb")
                upload_file_name = upload_file_name[:-4] + '.csv'
                os.remove('tmp/' + upload_file_name[:-4] + '.csv')



            # file to array

            csv_rows = []
            csvLines = []
            rows = []
            csv_dialect = {}
            csv_raw = ""

            # read/process the CSV file and find out about its dialect (csv params such as delimiter, line end...)
            # https://docs.python.org/2/library/csv.html#
            logger.debug("encoding %s", request.encoding)
            with TextIOWrapper(upload_file, encoding=request.encoding, errors='replace') as csv_file:
                # with TextIOWrapper(upload_file, encoding='utf-8') as csvfile:
                # the file is also provided in raw formatting, so users can appy changes (choose csv params) without reloading file 
                csv_raw = csv_file.read()
                 # TODO only one upload function!
                csv_rows, csv_dialect = process_csv(csv_file, form)
                request.session['csv_rows_num'] = len(csv_rows) - 1

                # check if file is correct
                publish_message = '<span class="trafo_green"><i class="fa fa-check-circle"></i> File seems to be okay.</span>'
                num_last_row = len(csv_rows[0])
                for i in range(1, len(csv_rows)):
                    if len(csv_rows[i]) != num_last_row:
                        logger.info("File seems to be either corrupted or it was loaded with wrong parameters! Line: " + str(i+1)+ ": "+ str(csv_rows[i]))
                        publish_message = '<span class="trafo_red"><i class="fa fa-exclamation-circle"></i> File seems to be corrupt or loaded with wrong parameters!</span><br><span>Line: ' + str(i+1) + ':'+str(csv_rows[i])+'</span>'
                        break

                # save file

                time1 = datetime.datetime.now()
                save_path = "filesaves/"
                session_id = request.session.session_key
                if request.user.is_authenticated():
                    logger.info('user authenticated: %s', request.user)
                    save_path += str(request.user)
                else:
                    logger.info('user NOT authenticated / anonymous: %s', session_id)
                    save_path += "anonymous"

                save_path += "/"
                save_path += str(session_id)
                save_path += "/"

                if not os.path.exists(save_path):
                    os.makedirs(save_path)
                
                path_and_file = os.path.join(os.path.expanduser(save_path), upload_file_name)
                request.session['save_path'] = path_and_file
                fout = open(path_and_file, "w")
                #f = csvfile.read()
                fout.write(csv_raw)#(bytes(csv_raw, 'UTF-8'))
                fout.close()  

                secs = datetime.datetime.now() - time1
                logger.info("writing file time: %s", str(secs))              

                request.session['csv_dialect'] = csv_dialect
                request.session['csv_rows'] = csv_rows
                #request.session['csv_raw'] = csv_raw

        if 'button_upload' in request.POST:
            time1 = datetime.datetime.now()

            logger.debug("UPLOAD BUTTON PRESSED")
            csv_rows = csv_rows[:11] if csv_rows else None

            request.session['csv_dialect'] = csv_dialect
            request.session['csv_rows'] = csv_rows
            #request.session['csv_raw'] = csv_raw
            if 'upload_file' in request.FILES:
                request.session['file_name'] = request.FILES['upload_file'].name
            # return redirect(reverse('csv-column-choice-view'))
            html_post_data = {
                'action': form_action,
                'form': form,
                'csvContent': request.session['csv_rows'],
                #'csvRaw': request.session['csv_raw'],
                #'csvDialect': request.session['csv_dialect'],
                'filename': request.session['file_name'],
                'publish_message': publish_message
            }

            secs = datetime.datetime.now() - time1
            logger.info("upload procedure time: %s" + str(secs))
            return render(request, 'transformation/csv_upload.html', html_post_data)

        if 'button_choose' in request.POST:
            # logger.info(request.POST['mapping_id'])
            request.session['model'] = json.loads(
                Mapping.objects.filter(id=request.POST['mapping_id'])[0].mappingFile.read().decode("utf-8"))
            form = UploadFileForm()
            return render(request, 'transformation/csv_upload.html', {'action': 1, 'form': form})

    # html GET, we get here when loading the page 'for the first time'
    else:  # if request.method != 'POST':
        logger.debug("PATH 4 - initial page call (HTML GET)")
        form = UploadFileForm()
        return render(request, 'transformation/csv_upload.html', {'action': 1, 'form': form})


def csv_column_choice(request):
    logger.info("VIEW csv_column_choice")
    form_action = 3
    publish_message = None
    form = CsvColumnChoiceForm(request.POST)
    request.session['processing_status'] = get_status_dict("csv_column_choice")

    time1 = datetime.datetime.now()

    if 'model' not in request.session:
        logger.info('creating model')
        time1 = datetime.datetime.now()
        arr = request.session['csv_rows']
        m = {"file_name": request.session['file_name'], "num_rows_total": request.session['csv_rows_num'], "num_cols_selected": len(arr[0]),
             "columns": [], "csv_dialect": request.session['csv_dialect'], "save_path": request.session['save_path'], "object_recons": {}, "object_recons_all": {}}
        f = -1
        c = -1

        try:

            for i, head in enumerate(arr[0]):
                m['columns'].append({'col_num_orig': i + 1, 'col_num_new': i + 1, 'header': {'orig_val': arr[0][i]}})

        except IndexError:
            logger.info("index error: col " + str(c) + ", field " + str(f))
        secs = datetime.datetime.now() - time1
        logger.info("model creation took " + str(secs))

        time1 = datetime.datetime.now()
        update_excerpt(m, start_row=0, num_rows=10)
        secs = datetime.datetime.now() - time1
        logger.info("update_excerpt took " + str(secs))

        request.session['model'] = m

    # has fields? if not, only scaffolding from model 'loaded' in data choice page of wizard
    elif 'model' in request.session and 'excerpt' not in request.session['model']:
        # when only a loaded model 'scaffolding'
        logger.info("model 'scaffolding' was loaded")

        if len(request.session['model']['columns']) != len(request.session['csv_rows'][0]):
            publish_message = "The file you tried to load does not fit the chosen transformation project. The number of columns is different."
        else:
            '''
            for i, col in enumerate(inverted_csv):
                request.session['model']['columns'][i]['fields'] = []
                for j, field in enumerate(col):
                    if j == 0:  # table header / first row
                        # column_obj['header'] = {"orig_val": field}
                        pass
                    else:
                        request.session['model']['columns'][i]['fields'].append({"orig_val": field, "field_num": j})
            '''

            request.session['model']['file_name'] = request.session['file_name']

            arr = request.session['csv_rows']
            m = request.session['model']
            f = -1
            c = -1

            try:

                for field in range(1, len(arr)):
                    f = field
                    for col in range(0, len(arr[field])):
                        c = col
                        if 'fields' not in m['columns'][col]:
                            m['columns'][col]['fields'] = []
                        m['columns'][col]['fields'].append({'orig_val': arr[field][col], 'field_num': field})

            except IndexError:
                logger.info("index error: col %s, field %s",  str(c), str(f))

    elif request.POST and form.is_valid() and 'hidden_model' in form.cleaned_data and form.cleaned_data['hidden_model']:
        logger.info("model existing")
        request.session['model'] = json.loads(form.cleaned_data['hidden_model'])

    html_post_data = {
        'rdfModel': json.dumps(request.session['model']),
        'action': form_action,
        'csvContent': request.session['csv_rows'][:11],
        'filename': request.session['file_name'],
        'publish_message': publish_message
    }
    if 'model' in request.session and 'rdfModel' not in html_post_data:
        logger.info("reducing...")
        redu = reduce_model(request.session['model'], 10)
        html_post_data['rdfModel'] = json.dumps(redu)
    request.session.modified = True
    return render(request, 'transformation/csv_column_choice.html', html_post_data)


def csv_subject(request):
    logger.info("VIEW csv_subject")

    form_action = 4
    form = SubjectForm(request.POST)
    request.session['processing_status'] = get_status_dict("csv_subject")
    if request.POST and form.is_valid() and form is not None:

        # content  is passed on via hidden html input fields

        request.session['model'] = json.loads(form.cleaned_data['hidden_model'])

        update_excerpt(model=request.session['model'], start_row=0, num_rows=10)
    html_post_data = {
        'rdfModel': json.dumps(request.session['model']),
        'action': form_action,
        'filename': request.session['file_name'],
    }
    return render(request, 'transformation/csv_subject.html', html_post_data)


def csv_predicate(request):
    logger.info("VIEW csv_predicate")
    form_action = 5
    form = PredicateForm(request.POST)
    request.session['processing_status'] = get_status_dict("csv_predicate")
    if request.POST and form.is_valid() and form is not None:
        # content  is passed on via hidden html input fields
        if 'hidden_model' in form.cleaned_data:
            request.session['model'] = json.loads(form.cleaned_data['hidden_model'])
            update_excerpt(request.session['model'], start_row=0, num_rows=10)

    html_post_data = {
        'action': form_action,
        'rdfModel': json.dumps(request.session['model']),
        'filename': request.session['file_name'],
    }
    return render(request, 'transformation/csv_predicate.html', html_post_data)


def csv_object(request):
    """
    """

    logger.info("VIEW csv_object")
    form_action = 6
    form = ObjectForm(request.POST)
    request.session['processing_status'] = get_status_dict("csv_object")
    if request.POST and form.is_valid():  # and form != None:
        # content  is passed on via hidden html input fields
        if 'hidden_model' in form.cleaned_data:
            request.session['model'] = json.loads(form.cleaned_data['hidden_model'])
        else:
            request.session['model'] = ""
            logger.info("no model")
    else:
        logger.info("form not valid!")

    num_rows_model = request.session['model']['num_rows_total']

    # pagination
    if "page" in request.GET and is_int(request.GET.get('page')):
        page = int(request.GET.get('page'))
    else:
        page = 1

    if "num" in request.GET and is_int(request.GET.get('num')):
        per_page = int(request.GET.get('num'))
    else:
        per_page = 10

    max_pages = num_rows_model // per_page
    if num_rows_model % per_page > 0:  # 'rest'
        max_pages += 1

    if page > num_rows_model / per_page:
        page = max_pages

    if max_pages > 15:
        paging_html = "<select>"
        for x in range(max_pages):
            f = (x * per_page) + 1
            t = f + per_page - 1
            if t > num_rows_model:
                t = num_rows_model
            sel = ""
            if x + 1 == page:
                sel = "selected"
            paging_html += '<option class="pagination-link" ' + sel + ' href="?page=' + str(x + 1) + '&num=' + str(
                per_page) + '">' + str(f) + '-' + str(t) + '</option>'
        #paging_html = paging_html[:-2]
        paging_html += "</select>"

    else:        
        paging_html = ""
        for x in range(max_pages):
            f = (x * per_page) + 1
            t = f + per_page - 1
            if t > num_rows_model:
                t = num_rows_model
            recent_page = ""
            if x + 1 == page:
                recent_page = " recent-page"
            paging_html += '<a class="pagination-link' + recent_page + '" href="?page=' + str(x + 1) + '&num=' + str(
                per_page) + '">' + str(f) + '-' + str(t) + '</a> |'
        paging_html = paging_html[:-2]


    row_num_select = '<select id="select-rows-per-page">'
    pages_arr = [10, 25, 50, 100]
    # insert a page amount in the the if it was modified in the url get params
    if per_page not in pages_arr:
        pages_arr.append(per_page)
    if num_rows_model not in pages_arr:
        pages_arr.append(num_rows_model)
    pages_arr = sorted(pages_arr)
    for p in pages_arr:
        if p <= num_rows_model:
            selected = ""
            if p == per_page:
                selected = " selected"
            row_num_select += "<option" + selected + ' href="?page=' + str(page) + '&num=' + str(p) + '">' + str(
                p) + "</option>"
    row_num_select += "</select>"

    start_row = page * per_page - per_page +1
    end_row = page * per_page

    if end_row > num_rows_model:
        end_row = num_rows_model

    update_excerpt(request.session['model'], start_row=start_row, num_rows=per_page)

    pagination = {
        'startRow': start_row,
        'endRow': end_row,
        'html': paging_html,
        'perPage': per_page,
        'page': page,
        'max_pages': max_pages,
        'num_rows': num_rows_model,
        'row_num_select_html': row_num_select}

    # pagination end

    html_post_data = {
        'pagination': pagination,
        'action': form_action,
        'rdfModel': json.dumps(request.session['model']),
        'filename': request.session['file_name'],
    }
    return render(request, 'transformation/csv_object.html', html_post_data)


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def csv_enrich(request):
    logger.info("VIEW csv_additional")
    form_action = 7
    form = EnrichForm(request.POST)
    request.session['processing_status'] = get_status_dict("csv_enrich")
    if request.POST and form.is_valid() and form != None:
        # content  is passed on via hidden html input fields

        if 'hidden_model' in form.cleaned_data:
            #reduced_model = json.loads(form.cleaned_data['hidden_model'])
            #request.session['model'] = update_model(request.session['model'], reduced_model)
            request.session['model'] = json.loads(form.cleaned_data['hidden_model']) 
            update_excerpt(request.session['model'], start_row=0, num_rows=10)

    # csv_rows_selected_columns = get_selected_rows_content(request.session)
    html_post_data = {
        'action': form_action,
        'rdfModel': json.dumps(request.session['model']),
        'filename': request.session['file_name'],
    }
    pass
    return render(request, 'transformation/csv_enrich.html', html_post_data)


def csv_publish(request):
    logger.info("VIEW csv_publish")
    form_action = 7  # refers to itself
    form = PublishForm(request.POST)
    publish_message = ""
    request.session['processing_status'] = get_status_dict("csv_publish")

    if request.POST and form.is_valid() and form != None:

        if 'hidden_model' in form.cleaned_data:
            request.session['model'] = json.loads(form.cleaned_data['hidden_model'])
            update_excerpt(request.session['model'], start_row=0, num_rows=10)

        if 'button_publish' in request.POST:
            payload = {'title': request.POST.get('name_publish'),
                       'content': model_to_triple_string(request.session['model']), 'format': 'text/rdf+n3'}
            # Please set the API_HOST in the settings file
            r = requests.post('http://' + API_HOST + '/api/datasource/create/', data=payload)
            j = json.loads(r.text)
            #logger.info(j["message"])
            publish_message = j["message"]

        if 'button_download' in request.POST:            
            new_fname = request.session['file_name'].rsplit(".", 1)[0] + ".n3"
            rdf_string = model_to_triple_string(request.session['model'])
            rdf_file = ContentFile(rdf_string.encode('utf-8'))
            response = HttpResponse(rdf_file, 'application/force-download')
            response.set_cookie('rdf_download_status', 'complete')
            response['Content-Length'] = rdf_file.size
            response['Content-Disposition'] = 'attachment; filename="' + new_fname + '"'
            request.session['processing_status'] = get_status_dict("finished download", 100)
            return response
        '''
        if 'button_r2rml' in request.POST:
            new_fname = request.session['file_name'].rsplit(".", 1)[0] + "_R2RML.ttl"
            r2rml_string = transform_to_r2rml(request.session['model'])
            r2rml_file = ContentFile(r2rml_string.encode('utf-8'))
            response = HttpResponse(r2rml_file, 'application/force-download')
            response['Content-Length'] = r2rml_file.size
            response['Content-Disposition'] = 'attachment; filename="' + new_fname + '"'
            request.session['processing_status'] = get_status_dict("finished download", 100)
            return response
        '''


        if 'button_close' in request.POST:
           return redirect('csv-upload-view')
        

        if 'save_mapping' in request.POST:
            # remove unwanted info from model
            m_light = model_light(request.session['model'])
            transformation_file = ContentFile(json.dumps(m_light).encode('utf-8'))
            mapping = Mapping(user=request.user, fileName=request.POST.get('name_mapping'),
                              csvName=request.session['save_path'])
            mapping.mappingFile.save(request.POST.get('name_mapping'), transformation_file)
            mapping.save()
            publish_message = "Mapping was saved."

    # csv_rows_selected_columns = get_selected_rows_content(request.session)
    html_post_data = {
        'publish_message': publish_message,
        'action': form_action,
        'rdfModel': json.dumps(request.session['model']),
        'filename': request.session['file_name'],
    }
    return render(request, 'transformation/csv_publish.html', html_post_data)



def json_response(func):
    """
    A decorator that takes a view response and turns it
    into json. If a callback is added through GET or POST
    the response is JSONP.
    """
    def decorator(request, *args, **kwargs):
        objects = func(request, *args, **kwargs)
        if isinstance(objects, HttpResponse):
            return objects
        try:
            data = json.dumps(objects)
            if 'callback' in request.REQUEST:
                # a jsonp response!
                data = '%s(%s);' % (request.REQUEST['callback'], data)
                return HttpResponse(data, "text/javascript")
        except:
            data = json.dumps(str(objects))
        return HttpResponse(data, "application/json")
    return decorator


@json_response
def status(request):
    """
    REST interface w/ HTTP GET params:
    callback: name of callback function
    uri: url to retrieve the prefix for, make sure to use url-encode
    (python urllib.urlencode(uri), JavaScript: encodeURIComponent(uri);)
    :param request: HTTP request
    :return: python dict
    """
    if 'processing_status' not in request.session:
        request.session['processing_status'] = "not set"
        logger.info("set session %s", request.session['processing_status'])
    result = request.session['processing_status'];
    return result


    
# ###############################################
#########       RDB                    ##########
# ###############################################
    
    

def rdb_select(request):

    print("VIEW rdb_select")
    form_action = 2
    if request.method == 'POST':
        form = DatabaseSelectForm(request.POST)
        if form.is_valid() and form != None:
            print("  form.is_valid() and form != None")
            schema = {}
            if form.cleaned_data['db_databasetype'] == 'MY': 
                db_databasetype = form.cleaned_data['db_databasetype']  #.encode('utf-8')
                res = get_mysql_cursor(form.cleaned_data['db_host'], form.cleaned_data['db_user'], form.cleaned_data['db_password'], form.cleaned_data['db_database'])
                cursor = res['cursor']
                if cursor:
                    res2 = {}
                    model = {}
                    res2 = get_mysql_fkeys(cursor)
                    fkeys = res2['fkeys']
                    request.session['fkeys'] = fkeys
                    request.session['host'] = form.cleaned_data['db_host']
                    request.session['db'] = form.cleaned_data['db_database']
                    request.session['user'] = form.cleaned_data['db_user']
                    request.session['password'] = form.cleaned_data['db_password']
                    request.session['databasetype'] = form.cleaned_data['db_databasetype']
                    res2 = get_mysql_tables(cursor, fkeys)
                    model = res2['model']
                    model['database'] = request.session['db']
                    request.session['model'] = model
                    mysql_disconnect(res['con'])
                
                    html_post_data = {
                        'action': form_action,
                        'form': form,
                        'model': model
                    }
                    schema = {'connection': 'success', 'fkeys': fkeys}
                    html_post_data.update(schema)
                else: # if cursor:
                    html_post_data = {
                        'action': 1,
                        'form': form,
                        'connection': 'failed'
                    }
                    schema = {'connection': 'failed', 'message': res['message']}
                    html_post_data.update(schema)
                    
            else : # if db_databasetype == 'MY' -> MySQL:
                schema = {'connection': 'failed', 'message': 'connection to ' + form.cleaned_data['db_databasetype'] + ' is not implemented yet'}
                html_post_data = {
                    'action': 1,
                    'form': form,
                    'connection': 'failed'
                }
        elif 'mapping_id' in request.POST: # QueryDict(request.body).get('tablepk'))
            print("  'mapping_id' in request.POST")
            form = DatabaseSelectForm()
            mapping_id = QueryDict(request.body).get('mapping_id')
            mapping = DbMapping.objects.get(pk=mapping_id)
            request.session['fkeys'] = ast.literal_eval(mapping.fkeys)
            request.session['host'] = mapping.host
            request.session['db'] = mapping.database
            request.session['user'] = mapping.dbuser
            request.session['password'] = mapping.password
            request.session['databasetype'] = mapping.type
            request.session['model'] = ast.literal_eval(mapping.model)
            current_page = mapping.current_page
            html_post_data = {
                'model': ast.literal_eval(mapping.model)
            }
            schema = {'connection': 'load', 'fkeys': ast.literal_eval(mapping.fkeys)}
            html_post_data.update(schema)
            
            if current_page == 1:
                form = DatabaseSelectForm()
                html_post_data.update({'action': 2})
                html_post_data.update({'form': form})
                return render(request, 'transformation/rdb_select.html', html_post_data)
            elif current_page == 2:
                form = DatabaseSQLForm()
                html_post_data.update({'action': 3})
                html_post_data.update({'form': form})
                return render(request, 'transformation/rdb_sql_select.html', html_post_data)
            elif current_page == 3:
                html_post_data.update({'action': 4})
                return render(request, 'transformation/rdb_column_choice.html', html_post_data)
            elif current_page == 4:
                html_post_data.update({'action': 5})
                return render(request, 'transformation/rdb_subject.html', html_post_data)
            elif current_page == 5:
                html_post_data.update({'action': 6})
                return render(request, 'transformation/rdb_predicate.html', html_post_data)
            elif current_page == 6:
                html_post_data.update({'action': 7})
                return render(request, 'transformation/rdb_object.html', html_post_data)
            elif current_page == 7:
                html_post_data.update({'action': 8})
                return render(request, 'transformation/rdb_enrich.html', html_post_data)
            elif current_page == 8:
                return render(request, 'transformation/rdb_publish.html', html_post_data)
        else: # if form.is_valid() and form != None:
            print("NOT form.is_valid() or form == None ")
            fkeys = request.session['fkeys']
            model = request.POST.get('hidden_model', "{}")
            model = ast.literal_eval(model)
            request.session['model'] = model
            html_post_data = {
                'action': form_action
            }
            form = DatabaseSelectForm()
            mymodel = {'model': model}
            html_post_data.update(mymodel)
            schema = {'connection': 'back', 'fkeys': fkeys}
            html_post_data.update(schema)
            html_post_data.update({'form': form})
        return render(request, 'transformation/rdb_select.html', html_post_data)
    else:  # if request.method == 'POST':
        print("PATH 4 - initial page call (HTML GET)")
        form = DatabaseSelectForm()
        return render(request, 'transformation/rdb_select.html', {'action': 1, 'form': form})


def rdb_sql_select(request):
    print("VIEW rdb_sql_select")
    form_action = 3
    fkeys = request.session['fkeys']
    model = request.session['model']

    if request.method == 'POST':
        form = DatabaseSQLForm(request.POST)
        if form.is_valid() and form != None:
            if request.session['databasetype'] == 'MY': 
                sql_query = form.cleaned_data['sql_query']
                sql_name = form.cleaned_data['sql_name']
                if sql_query != '' and sql_query != None:
                    schema = {'connection': '', 'fkeys': fkeys}
                    html_post_data = {
                        'action': 2,
                        'form': form,
                        'model': model
                    }
                    html_post_data.update(schema)
                    return render(request, 'transformation/rdb_sql_select.html', html_post_data)             
                else: # initial post 
                    schema = {'connection': '', 'fkeys': fkeys}
                    html_post_data = {
                        'action': 2,
                        'form': form,
                        'model': model
                    }
                    html_post_data.update(schema)
                    return render(request, 'transformation/rdb_sql_select.html', html_post_data)
            else : #if db_databasetype == 'MySQL':
                schema = {'connection': 'failed', 'message': 'connection to ' + db_databasetype + ' is not implemented yet'}
                html_post_data = {
                    'action': 2,
                    'form': form,
                    'connection': 'failed'
                }
        else: # if form.is_valid() and form != None:
            logger.info("NOT form.is_valid() or form == None ")
            model = request.POST.get('hidden_model', "{}")
            model = ast.literal_eval(model)
            request.session['model'] = model
            html_post_data = {
                'action': form_action
            }
            mymodel = {'model': model}
            html_post_data.update(mymodel)
            schema = {'connection': '', 'fkeys': fkeys}
            html_post_data.update(schema)

        return render(request, 'transformation/rdb_sql_select.html', html_post_data)
    else:  # if request.method == 'POST':
        form = DatabaseSQLForm()
        schema = {'connection': '', 'fkeys': fkeys}
        html_post_data = {
            'action': 2,
            'form': form,
            'connection': '',
            'model': model
         }
        html_post_data.update(schema)
        return render(request, 'transformation/rdb_sql_select.html', html_post_data)


# AJAX functions

def rdb_delete_table(request):
    if request.method == 'DELETE':
        table = DbTable.objects.get(pk=int(QueryDict(request.body).get('tablepk')))
        table.delete()
        response_data = {}
        response_data['msg'] = 'table was deleted.'
        return HttpResponse(
            json.dumps(response_data),
            content_type="application/json"
        )
    else:
        return HttpResponse(
            json.dumps({"nothing to see": "this isn't happening"}),
            content_type="application/json"
        )


def rdb_get_sql_table(request):
    print("rdb_get_sql_table()")
    fkeys = request.session['fkeys']
    sql_name = QueryDict(request.body).get('sql_name')
    sql_query = QueryDict(request.body).get('sql_query')
    if sql_query != '' and sql_query != None:
        res = get_mysql_cursor(request.session['host'], request.session['user'], request.session['password'], request.session['db'])
        cursor = res['cursor']
        table_res = get_mysql_sql_table_data2(cursor, sql_name, sql_query, fkeys, 10)
        mysql_disconnect(res['con'])
        response_data = {}
        response_data.update(table_res)
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        return HttpResponse(json.dumps({"nothing to see": "this isn't happening"}), content_type="application/json")

def rdb_get_table_values(request):
    logger.info("rdb_get_table_values()")
#    table_name = QueryDict(request.body).get('table_name')
    sql_query = QueryDict(request.body).get('sql_query')
    sql_query_all = QueryDict(request.body).get('sql_query_all')
#    page = QueryDict(request.body).get('page')
#    num = QueryDict(request.body).get('num')
    if sql_query != '' and sql_query != None:
        res = get_mysql_cursor(request.session['host'], request.session['user'], request.session['password'], request.session['db'])
        cursor = res['cursor']
        table_res = get_mysql_sql_table_data3(cursor, sql_query, sql_query_all)
        mysql_disconnect(res['con'])
        response_data = {}
        response_data.update(table_res)
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        return HttpResponse(json.dumps({"nothing to see": "this isn't happening"}), content_type="application/json")
    

def rdb_column_choice(request):
    logger.info("VIEW rdb_column_choice")
    form_action = 4
    fkeys = request.session['fkeys']
    model = request.session['model']

    if request.method == 'POST':
        publish_message = None
        schema = {'fkeys': fkeys}
        model = request.POST.get('hidden_model', "{}")
        model = ast.literal_eval(model)
        request.session['model'] = model
        html_post_data = {
            'action': form_action
        }
        mymodel = {'model': model}
        html_post_data.update(mymodel)
        html_post_data.update(schema)
        return render(request, 'transformation/rdb_column_choice.html', html_post_data)
    
    else:  # if request.method == 'POST':
        schema = {'connection': '', 'fkeys': fkeys}
        html_post_data = {
            'action': 4,
            'connection': '',
            'model': model
         }
        html_post_data.update(schema)
        return render(request, 'transformation/rdb_column_choice.html', html_post_data)


def rdb_subject(request):
    logger.info("VIEW rdb_subject")
    fkeys = request.session['fkeys']
    model = request.session['model']
    form_action = 5
    if request.method == 'POST':
        source = request.POST.get('hidden_source', "4")
        model = request.POST.get('hidden_model', "{}")
        model = ast.literal_eval(model)
        request.session['model'] = model

    schema = {'fkeys': fkeys}
    html_post_data = {
        'action': form_action,
         'model': model
    }
    html_post_data.update(schema)
    return render(request, 'transformation/rdb_subject.html', html_post_data)


def rdb_predicate(request):
    logger.info("VIEW rdb_predicate")
    form_action = 6
    fkeys = request.session['fkeys']
    model = request.session['model']
    if request.method == 'POST':
        source = request.POST.get('hidden_source', "4")
        model = request.POST.get('hidden_model', "{}")
        model = ast.literal_eval(model)
        request.session['model'] = model
        
    html_post_data = {
        'action': form_action,
        'model': model
    }
    schema = {'fkeys': fkeys}
    html_post_data.update(schema)
    return render(request, 'transformation/rdb_predicate.html', html_post_data)


def rdb_object(request):
    logger.info("VIEW rdb_object")
    form_action = 7
    if request.method == 'POST':
        model = request.POST.get('hidden_model', "{}")
        model = ast.literal_eval(model)
        request.session['model'] = model
    model = request.session['model']
    fkeys = request.session['fkeys']
    html_post_data = {
        'action': form_action,
        'model': model
    }
    schema = {'fkeys': fkeys}
    html_post_data.update(schema)
    return render(request, 'transformation/rdb_object.html', html_post_data)


def rdb_enrich(request):
    logger.info("VIEW rdb_enrich")
    form_action = 8
    if request.method == 'POST':
        model = request.POST.get('hidden_model', "{}")
        model = ast.literal_eval(model)
        request.session['model'] = model
    model = request.session['model']
    fkeys = request.session['fkeys']
    html_post_data = {
        'action': form_action,
        'model': model
    }
    schema = {'fkeys': fkeys}
    html_post_data.update(schema)
    return render(request, 'transformation/rdb_enrich.html', html_post_data)


def rdb_save_mapping(request):

    logger.info("rdb_save_mapping()")
#    logger.info("request:")
#    logger.info(request)
    try:
        publish_message = ""
        model = request.session['model']
        fkeys = request.session['fkeys']
#        logger.info("model: ")
#        logger.info(model)
        
        if request.method == 'POST':
            model = QueryDict(request.body).get('model')
            #model = request.POST.get('model', "{}")
#            logger.info("model: ")
#            logger.info(model)
            model = ast.literal_eval(model)
            current_page = QueryDict(request.body).get('current_page')
#            logger.info("model: ")
#            logger.info(model)
#            logger.info("current_page:")
#            logger.info(current_page)

            request.session['model'] = model
            transformation_file = ContentFile(json.dumps(model).encode('utf-8'))
            has_port = False
            
            if 'port' in request.session:
                has_port = True
            if has_port:
                mapping = DbMapping(
                    user = request.user, 
                    host = request.session['host'], 
                    port = request.session['port'],
                    database = request.session['db'],
                    name = request.POST.get('name_mapping'),
                    dbuser = request.session['user'],
                    password = request.session['password'],
                    type = request.session['databasetype'],
                    model = model,
                    fkeys = fkeys,
                    current_page = current_page
                    )
            else:
                mapping = DbMapping(
                    user = request.user, 
                    host = request.session['host'], 
                    database = request.session['db'],
                    name = request.POST.get('name_mapping'),
                    dbuser = request.session['user'],
                    password = request.session['password'],
                    type = request.session['databasetype'],
                    model = model,
                    fkeys = fkeys,
                    current_page = current_page
                    )
            mapping.save()
            return HttpResponse(json.dumps({"message": "mapping saved"}), content_type="application/json")
    except:
        logger.info("ERROR")
        logger.info(sys.exc_info()[1])
        return HttpResponse(json.dumps({"message": "this isnt happening"}), content_type="application/json")


def rdb_publish(request):
    logger.info("VIEW rdb_publish")
    publish_message = ""
    model = request.session['model']
    fkeys = request.session['fkeys']

    if request.method == 'POST':
        model = request.POST.get('hidden_model', "{}")
        model = ast.literal_eval(model)
 
        request.session['model'] = model
     
        if 'button_publish' in request.POST:
            try:
                API_HOST = "linda.epu.ntua.gr:8000"
                payload = {'title': request.POST.get('name_publish'), 'content': transformdb2n3(model, request), 'format': 'text/rdf+n3'}
                #Please set the API_HOST in the settings file

                r = requests.post('http://' + API_HOST + '/api/datasource/create/', data=payload)
                j = json.loads(r.text)
                logger.info(j["message"])
                publish_message = j["message"]
            except:
                logger.info("ERROR")
                logger.info(sys.exc_info()[1])
                publish_message = sys.exc_info()[1]


        if 'button_download' in request.POST:
            new_fname = model['database'].rsplit(".", 1)[0]+".n3"
            rdf_string = transformdb2n3(model, request)
            rdf_file = ContentFile(rdf_string.encode('utf-8'))
            response = HttpResponse(rdf_file, 'application/force-download')
            response['Content-Length'] = rdf_file.size
            response['Content-Disposition'] = 'attachment; filename="'+new_fname+'"'
            return response

        if 'button_r2rml' in request.POST:
            new_fname = model['database'].rsplit(".", 1)[0]+"_R2RML.ttl"
            r2rml_string = transformdb2r2rml(model)
            r2rml_file = ContentFile(r2rml_string.encode('utf-8'))
            response = HttpResponse(r2rml_file, 'application/force-download')
            response['Content-Length'] = r2rml_file.size
            response['Content-Disposition'] = 'attachment; filename="'+new_fname+'"'
            return response

        if 'save_mapping' in request.POST:
            transformation_file = ContentFile(json.dumps(model).encode('utf-8'))
            has_port = False
            
            if 'port' in request.session:
                has_port = True
            if has_port:
                mapping = DbMapping(
                    user = request.user, 
                    host = request.session['host'], 
                    port = request.session['port'],
                    database = request.session['db'],
                    name = request.POST.get('save_mapping'),
                    dbuser = request.session['user'],
                    password = request.session['password'],
                    type = request.session['databasetype'],
                    model = model,
                    fkeys = fkeys
                    )
            else:
                mapping = DbMapping(
                    user = request.user, 
                    host = request.session['host'], 
                    database = request.session['db'],
                    name = request.POST.get('save_mapping'),
                    dbuser = request.session['user'],
                    password = request.session['password'],
                    type = request.session['databasetype'],
                    model = model,
                    fkeys = fkeys
                    )
            mapping.save()
            publish_message = "mapping saved"
        if 'button_restart' in request.POST:
            return render(request, 'transformation/data_choice.html')

    html_post_data = {
        'publish_message': publish_message,
        'model': model
    }
    schema = {'fkeys': fkeys}
    html_post_data.update(schema)
    return render(request, 'transformation/rdb_publish.html', html_post_data)

    
    
# ###############################################
#########       END RDB                ##########
# ###############################################

    
    
# ###############################################
#  OTHER FUNCTIONS
# ###############################################

def model_light(model):
    m2 = model.copy()
    #del m2['object_recons']
    m2['object_recons'] = {}
    del m2['excerpt']
    #m2['excerpt'] = []
    #del m2['file_name']
    #m2['file_name'] = ""
    return m2


def get_status_dict(status_str, percent=100):
    return {'status': status_str,'time': time.time(), 'percent': percent}


def ask_oracle_for_rest(model, column):
    """
    This function reconciles all fields in table that were have not been
    reconciled in the object step in the frontend. The model parameter is manipulated directly.
    :param model: json 'model' that contains the frontend settings and reconciliation data
    :param column: needs to be ORIGINAL column num, not column num of selected columns
    :return: Whether or not model could be manipulated successfully as boolean
    """

    if 'object_recons' not in model or str(column) not in model['object_recons']:
        return False
    obj_recons = model['object_recons'][str(column)]

    content = file_to_array(request=None, model=model, start_row=0, num_rows=-1)

    # store all fields of one column in single array
    one_row = []
    for row in content['rows']:
        one_row.append(row[int(column)-1])

    # no duplicates
    one_row = list(set(one_row))

    del content

    # json header
    headers = {'Accept': 'application/json'}

    for queryString in one_row:
        if queryString not in obj_recons:
            url = 'http://lookup.dbpedia.org/api/search/KeywordSearch?QueryString=' + queryString
            r = requests.get(url, headers=headers)
            json_result = json.loads(r.text)['results']#[0]['uri']
            if type(json_result) == "list" and len(json_result) > 0:
                # TODO could be more general
                url_array = json_result.rsplit("/", 1)
                suffix = url_array[-1]
                uri = url_array[0]
                x = {'prefix': 'dbpedia', 'suffix': suffix, 'url': uri}
                obj_recons[queryString] = x

    return True


def get_selected_rows_content(session):
    """
    returns only the contents of the columns that were chosen in the html form from the session data
    for step 2 (csv column selection) in frontend
    :param session: django session object, contains CSV data
    :return: array containing rows that were marked as 'selected' in frontend only
    """
    result = []
    # write column numbers in array
    col_nums = []
    for col_num in session['selected_columns']:
        col_nums.append(col_num.get("col_num_orig"))

    for row in session['csv_rows']:
        tmp_row = []
        for cn in col_nums:
            tmp_row.append(row[cn - 1])
        result.append(tmp_row)
    return result


def process_csv(csv_file, form):
    """
    Processes the CSV File and converts it to a 2dim array.
    Uses either the CSV parameters (delimiter, quotechars,...) specified in the HTML form if those exist
    or the auto-detected params instead.
    :param csv_file: fiel containing CSV data
    :param form: django form object that should contain CSV parameters from the CSV upload page (frontend) of the transformation tool
    """
    csv_dialect = {}
    csv_rows = []
    csv_file.seek(0)
    # Sniffer guesses CSV parameters / dialect
    # when error 'could not determine delimiter' -> raise bytes to sniff
    dialect = csv.Sniffer().sniff(csv_file.read(10240))
    csv_file.seek(0)
    # ['delimiter', 'doublequote', 'escapechar', 'lineterminator', 'quotechar', 'quoting', 'skipinitialspace']
    csv_dialect['delimiter'] = dialect.delimiter
    csv_dialect['escape'] = dialect.escapechar
    csv_dialect['quotechar'] = dialect.quotechar
    csv_dialect['line_end'] = dialect.lineterminator.replace('\r', 'cr').replace('\n', 'lf')

    # use csv params / dialect chosen by user if specified
    # to avoid '"delimiter" must be an 1-character string' error, I encoded to utf-8
    # http://stackoverflow.com/questions/11174790/convert-unicode-string-to-byte-string
    if form.is_valid() and form is not None:
        if form.cleaned_data['delimiter'] != "":
            dialect.delimiter = form.cleaned_data['delimiter']  # .encode('utf-8')
        if form.cleaned_data['escape'] != "":
            dialect.escapechar = form.cleaned_data['escape']  # .encode('utf-8')
        if form.cleaned_data['quotechar'] != "":
            dialect.quotechar = form.cleaned_data['quotechar']  # .encode('utf-8')
        if form.cleaned_data['line_end'] != "":
            dialect.lineterminator = form.cleaned_data['line_end']  # .encode('utf-8')

        csv_reader = csv.reader(csv_file, dialect)

        for row in csv_reader:
            csv_rows.append(row)

        # removal of blanks, especially special blanks \xA0 etc.
        for i, rowa in enumerate(csv_rows):
            for j, field in enumerate(rowa):
                csv_rows[i][j] = field.strip()

        return [csv_rows, csv_dialect]
    else:
        logger.info("Form invalid")
        return None

'''
def transform_to_r2rml(model):
    """
    Transforms the data in the json 'model' to a R2RML representation.
    R2RML is a language for expressing customized mappings from relational databases to RDF datasets.
    This function is intended to be used for the RDB version of the transformation tool.
    :param model: json 'model' that contains the frontend settings and reconciliation data
    :return: string representation of R2RML
    """
    # head = json.load(model)

    subject = model["subject"]
    columns = model["columns"]
    our_prefix = "demo"
    subject_types = []
    output = ""

    if "enrich" in model:
        for enr in model["enrich"]:
            subject_types.append(enr["url"])

    output = "@prefix rr: <http://www.w3.org/ns/r2rml#>.\n" \
             "@prefix " + our_prefix + ": <" + subject[
                 "base_url"] + ">.\n\n" + our_prefix + ":TriplesMap a rr:TriplesMapClass;\n" \
                                                      "\trr:logicalTable [ rr:tableName \"" + model[
                 "file_name"] + "\" ];\n\n\trr:subjectMap [ rr:template \"" + \
             subject["base_url"] + subject["skeleton"] + "\""

    for s in subject_types:
        output += ";\n\t\trr:class " + s

    output += "\n\t];  # of columns selected: " + str(model["num_cols_selected"])

    for column in columns:
        if (column["col_num_new"] >= 0) and ("predicate" in column):
            predicate = column["predicate"]
            header = column["header"]
            output += ";\n\trr:predicateObjectMap [\n\t\trr:predicateMap [ rr:predicate " + predicate[
                "url"] + " ];\n\t\t" \
                         "rr:ObjectMap [ rr:column \"" + header["orig_val"] + "\" ]\n\t]"

    output += "."

    return output
'''

def model_to_triple_string(model, request=None):
    """
    Builds an string with RDF triples from the JSON 'model'.
    (Eventually, the string is to be returned to the frontend to download as a file)
    :param model: json 'model' that contains the frontend settings and reconciliation data
    :return: a 3xn array, representing RDF data
    """
    rdf_n3 = ""
    rdf_array = model_to_triples(model)

    for row in rdf_array:  # ast.literal_eval(request.session['rdf_array']):#['rdf_array']:
        for elem in row:
            elem = elem.replace(",", "\\,")  # escape commas
            if elem[-1:] == ".":  # cut off as we had problems when uploading some uri like xyz_inc. with trailing dot
                elem = elem[:-1]
            rdf_n3 += elem + " "
        rdf_n3 += ".\n"

    return rdf_n3


def model_to_triples(model):
    """
    Builds an Array with RDF triples from the JSON 'model'
    :param model: json 'model' that contains the frontend settings and reconciliation data
    :return: a 3xn array, representing RDF data
    """

    time1 = datetime.datetime.now()

    #num_fields_in_row_rdf = len(model['columns'][0]['fields'])
    num_fields_in_row_rdf = model['num_rows_total']
    num_total_cols = 0

    # count
    for col in model['columns']:
        if col['col_num_new'] > - 1:
            num_total_cols += 1

    num_enrichs = 0
    if 'enrich' in model:
        num_enrichs = len(model['enrich'])

    num_total_fields_rdf = num_fields_in_row_rdf * num_total_cols + num_fields_in_row_rdf * num_enrichs

    skeleton = model['subject']['skeleton']
    base_url = model['subject']['base_url']

    subject = "<?subject>"
    if skeleton != "":
        subject = "<" + base_url + skeleton + ">"

    # contains names that are needed for subject creation
    skeleton_array = re.findall("\{(.*?)\}", skeleton)

    rdf_array = [[subject, "<?p>", "<?o>"] for x in range(0, num_total_fields_rdf)]


    prefix_dict = {}

    complete_array = file_to_array(model=model)['rows']

    time = datetime.datetime.now()

    # objects
    count1 = 0
    for i, col in enumerate(model['columns']):
        if col['col_num_new'] > - 1:
            ask_oracle_for_rest(model, col['col_num_orig'])
            count2 = count1
            add = ""
            if 'object_method' in col and col['object_method'] == "data type":
                add = "^^" + col['data_type']['prefix'] + ":" + col['data_type']['suffix']
                prefix_dict[col['data_type']['prefix']] = col['data_type']
            for j, field in enumerate(complete_array):
                elem = field[col['col_num_orig']-1]
                if 'object_method' in col and col['object_method'] == "reconciliation" and 'object_recons' in model and str(i+1) in model['object_recons'] and elem in model['object_recons'][str(i+1)]:
                    rdf_array[count2][2] = model['object_recons'][str(i+1)][elem]['prefix']+":"+model['object_recons'][str(i+1)][elem]['suffix']
                    prefix_dict[model['object_recons'][str(i+1)][elem]['prefix']] = model['object_recons'][str(i+1)][elem]
                else:
                    rdf_array[count2][2] = '"' + elem + '"' + add
                count2 += num_total_cols + num_enrichs
            count1 += 1

    secs = datetime.datetime.now() - time
    logger.info("objects creation time %s", str(secs))
    time = datetime.datetime.now()

    # subjects
    row_length = model['num_rows_total']
    if 'blank_nodes' in model['subject'] and model['subject']['blank_nodes'] == "true":
        for i, col in enumerate(model['columns']):
            counter = 0
            counter2 = 0
            if col['col_num_new'] > - 1:
                for row_num in range(0, row_length):
                    for x in range(counter, counter + num_total_cols + num_enrichs):
                        rdf_array[x][0] = "_:" + to_letters(counter2)
                    counter += num_total_cols + num_enrichs
                    counter2 += 1
    else:
        for i, s in enumerate(skeleton_array):
            for col in model['columns']:
                counter = 0
                if col['col_num_new'] > - 1:
                    for row_num in range(0, row_length):
                        field = complete_array[row_num][col['col_num_orig']-1]
                        if col['header']['orig_val'] == s:
                            for x in range(counter, counter + num_total_cols + num_enrichs):
                                if x == counter:
                                    #TODO translate url into right format instead of only .replace(" ", "%20")
                                    rdf_array[counter][0] = rdf_array[counter][0].replace("{" + s + "}", field.replace(" ", "%20"))
                                else:
                                    rdf_array[x][0] = rdf_array[counter][0]
                        counter += num_total_cols + num_enrichs

    secs = datetime.datetime.now() - time
    logger.info("subjects creation time %s", str(secs))
    time = datetime.datetime.now()

    # predicates
    count1 = 0
    for col in model['columns']:
        if col['col_num_new'] > - 1:
            url = col['predicate']['prefix']['url']
            prefix = col['predicate']['prefix']['prefix']
            suffix = col['predicate']['prefix']['suffix']
            if prefix == "" or suffix == "":
                u = "<"+url+">"
            else:
                u = prefix + ":" + suffix
                prefix_dict[prefix] = col['predicate']['prefix']
            for x in range(0, num_fields_in_row_rdf):
                rdf_array[count1 + x * (num_total_cols + num_enrichs)][1] = u
            count1 += 1

    secs = datetime.datetime.now() - time
    logger.info("predicates creation time %s", str(secs))
    time = datetime.datetime.now()

    if 'enrich' in model:
        for enr_count, enr in enumerate(model['enrich']):
            enrich_uri = ""
            if enr['prefix']['prefix'] == "" or enr['prefix']['suffix'] == "":
                enrich_uri = "<" + enr['prefix']['url'] + ">"
            else:
                enrich_uri = enr['prefix']['prefix'] + ":" + enr['prefix']['suffix']
                prefix_dict[enr['prefix']['prefix']] = enr['prefix']
            counter = num_total_cols + enr_count
            while counter < len(rdf_array):
                rdf_array[counter][1] = "a"
                rdf_array[counter][2] = enrich_uri
                counter += num_total_cols + num_enrichs

    secs = datetime.datetime.now() - time
    logger.info("enrich creation time %s", str(secs))
    time = datetime.datetime.now()

    prefix_array = []
    for x in prefix_dict:
        x1 = x + ":"
        x2 = "<" + prefix_dict[x]['url'] + ">"
        prefix_array.append(["@prefix", x1, x2])


    secs = datetime.datetime.now() - time
    logger.info("prefix creation time %s", str(secs))
    time = datetime.datetime.now()

    secs = datetime.datetime.now() - time1
    logger.info("RDF creation time %s", str(secs))

    return prefix_array + rdf_array
    #return rdf_array


def to_letters(num):
    """
    Transforms numbers to letters, e.g. 0 -> A, 1 -> B, 27 -> AB,...
    :param num: number
    :return: letter(s)
    """
    # A = 65, Z = 90 chr ord
    dev = num // 26
    mod = num % 26
    if dev > 0:
        return to_letters(dev - 1) + chr(mod + 65)
    else:
        return chr(mod + 65)


def update_excerpt(model, start_row=0, num_rows=-1):
    """
    Includes an excerpt of the model content as an array in 'excerpt' property of the model.
    also holds values about where the excerpt begins and how big it is.
    {'rows': csv_array, 'start_row': start_row, 'num_rows': num_rows, 'total_rows_num': row_count}
    :param model: json 'model' that contains the frontend settings and reconciliation data
    :param start_row: row to start from, default = 0
    :param num_rows: number of rows to include in model, default = all rows
    """
    if not model:
        logger.info("no model!")
        return

    # check if calculation of new excerpt is needed
    if 'excerpt' in model and model['excerpt']['num_rows'] == num_rows and model['excerpt']['start_row'] == start_row:
        return model
    else:
        model['excerpt'] = file_to_array(model=model, start_row=start_row, num_rows=num_rows)


def file_to_array(request=None, model=None, start_row=0, num_rows=-1):
    """
    Reads file in model['save_path'] and returns contents as array.
    Either django HTTP request object containing 'save_path' and 'csv_dialect', or LinDA JSON 'model' parameter must exist.
    Prefers model parameter if both are present.
    :param request: HTTP request
    :param model: LinDA JSON model
    :param start_row: row to start from, default = 0
    :param num_rows: number of rows to include in model, default = all rows
    :return: a python dict like: {'rows': csv_array, 'start_row': start_row, 'num_rows': num_rows, 'total_rows_num': row_count}
    """

    time1 = datetime.datetime.now()

    # do not count header row
    start_row_original = start_row
    start_row += 1

    path_and_file = None
    csv_dialect = None
    encoding = None
    row_count = None

    if model is not None:
        if 'save_path' in model and 'csv_dialect' in model:
            path_and_file = model['save_path']
            csv_dialect = model['csv_dialect']
            encoding = "UTF-8"
            if 'num_rows_total' in model:
                row_count = model['num_rows_total']
        else:
            logger.info("model param for file_to_array function is invalid")
    elif request is not None:
        if 'save_path' in request.session and 'csv_dialect' in request.session:
            path_and_file = request.session['save_path']
            csv_dialect = request.session['csv_dialect']
            encoding = request.encoding
        else:
            logger.info("request param for file_to_array function is invalid")
    else:
        logger.info("request and model parameters both None in file_to_array function")
        return False

    #TODO is user exists
    # mappings = Mapping.objects.filter(user=request.user.id)
    # file_name = mappings.

    csv_array = []

    if not os.path.exists(path_and_file):
        logger.info("File %s does not exist!", str(path_and_file))
    else:
        f = open(path_and_file, "rb")
        with TextIOWrapper(f, encoding=encoding) as csv_file:
            #TODO performance: maybe not read the whole file...
            '''
            csv_dialect['delimiter'] = dialect.delimiter
            csv_dialect['escape'] = dialect.escapechar
            csv_dialect['quotechar'] = dialect.quotechar
            csv_dialect['line_end'] = dialect.lineterminator.replace('\r', 'cr').replace('\n', 'lf')
            '''
            csv_reader = csv.reader(csv_file, lineterminator=csv_dialect['line_end'].replace('cr', '\r').replace('lf', '\n'), escapechar=csv_dialect['escape'], quotechar=csv_dialect['quotechar'], delimiter=csv_dialect['delimiter'])

            if row_count is None:
                row_count = sum(1 for row in csv_reader)
                f.seek(0)

            # if params not fitting
            if start_row + num_rows >= row_count:
                start_row = row_count - num_rows
                if start_row <= 0:
                    # take all
                    start_row = 1
                    num_rows = row_count
            if num_rows == -1:
                start_row = 1
                num_rows = row_count

            r = range(start_row, start_row + num_rows)
            maxi = max(r)
            for i, row in enumerate(csv_reader):
                if i in r:
                    csv_array.append(row)
                    if i > maxi:
                        break

            # removal of blanks, especially special blanks \xA0 etc.
            for i, row in enumerate(csv_array):
                for j, field in enumerate(row):
                    csv_array[i][j] = field.strip()

    secs = datetime.datetime.now() -time1
    logger.info("%d / %d rows read from file in %s", num_rows, row_count, str(secs))

    return {'rows': csv_array, 'start_row': start_row_original, 'num_rows': num_rows}


def delete_unused_tmp_files():    
    """
    This checks for unused temporary files of which the session has expired.
    """

    logger.info("Checking for unused tmp files...")

    sessions = Session.objects.filter(expire_date__gte=timezone.now())

    fresh_sessions = []

    for session in sessions:
        fresh_sessions.append(session.session_key)

    '''
    a_dir = 'filesaves/anonymous/'

    for dir in [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]:
        if dir not in fresh_sessions:
            logger.info("ALT:")
            shutil.rmtree(a_dir + dir)
        else:
            logger.info("FRISCH:")
        logger.info(dir)
    '''

    a_dir = 'filesaves/'

    for dir_user in [name for name in os.listdir(a_dir)
                if os.path.isdir(os.path.join(a_dir, name))]:
        #users
        #logger.info("dir1", dir_user)
        for dir_session in [name for name in os.listdir(a_dir+dir_user)
                if os.path.isdir(os.path.join(a_dir+dir_user, name))]:
            if dir_user == "anonymous": # user not logged in / anonymous
                if dir_session not in fresh_sessions:
                    shutil.rmtree(a_dir+ dir_user + '/' + dir_session)
                    logger.info("deleted mapping %s%s/%s", a_dir, dir_user, dir_session)
            else: # user logged in
                #mapping = Mapping(user=request.user, fileName=request.POST.get('name_mapping'),
                #              csvName=request.session['save_path'])
                mappings = Mapping.objects.filter(csvName__contains=dir_session)
                #for map in mappings:
                #    logger.info(str(map.csvName))
                if len(mappings) == 0:
                    #if we have no saved mapping for the dir, we delete it
                    logger.info("deleted mapping %s%s/%s", a_dir, dir_user, dir_session)
                    shutil.rmtree(a_dir + dir_user + '/' + dir_session)

 # ###############################################
#########       RDB                    ##########
# ###############################################

field_type = {
     0: 'DECIMAL',
     1: 'TINY',
     2: 'SHORT',
     3: 'int',
     4: 'FLOAT',
     5: 'DOUBLE',
     6: 'NULL',
     7: 'TIMESTAMP',
     8: 'LONGLONG',
     9: 'INT24',
     10: 'DATE',
     11: 'TIME',
     12: 'DATETIME',
     13: 'YEAR',
     14: 'NEWDATE',
     15: 'VARCHAR',
     16: 'BIT',
     246: 'NEWDECIMAL',
     247: 'INTERVAL',
     248: 'SET',
     249: 'TINY_BLOB',
     250: 'MEDIUM_BLOB',
     251: 'LONG_BLOB',
     252: 'BLOB',
     253: 'varchar',
     254: 'char',
     255: 'GEOMETRY' }


field_null_allowed = {
     0: '',
     1: 'NOT NULL',
}

#field_null_allowed = {
#     0: 'NOT NULL',
#     1: '',
#}

mysql_flags = {
    1: 'NOT_NULL',                  ###          0000 0000 0001
    2: 'PRI_KEY',                   ###          0000 0000 0010
    4: 'UNIQUE_KEY',                ###          0000 0000 0100
    8: 'MULTIPLE_KEY',              ###          0000 0000 1000
    16: 'BLOB',                     ###          0000 0001 0000
    32: 'UNSIGNED',                 ###          0000 0010 0000
    64: 'ZEROFILL',                 ###          0000 0100 0000
    128: 'BINARY',                  ###          0000 1000 0000
    256: 'ENUM',                    ###          0001 0000 0000
    512: 'AUTO_INCREMENT',          ###          0010 0000 0000
    1024: 'TIMESTAMP',              ###          0100 0000 0000
    2048: 'SET',                    ###          1000 0000 0000
    32768: 'NUM',                   ###   0 1000 0000 0000 0000
    16384: 'PART_KEY',              ###   0 0100 0000 0000 0000
    32768: 'GROUP',                 ###   0 1000 0000 0000 0000
    65536: 'UNIQUE' }               ###   1 0000 0000 0000 0000
     # 50 = 11 0010 -> PRI_KEY, BLOB, UNSIGNED
     # 3  =      11 -> NOT_NULL, PRI_KEY
     # 6 =      110 -> UNIQUE_KEY, PRI_KEY
     # 11 =    1011 -> MULTIPLE_KEY, PRI_KEY, NOT_NULL

# from transformation/static/js/common.js
# from http://linda.epu.ntua.gr:8000/api/vocabularies/versions/
lindaGlobals_prefixes = {
    'http://www.ontotext.com/proton/protontop#': 'ptop',
    'http://www.openarchives.org/ore/terms/': 'ore',
    'http://www.opengis.net/ont/geosparql': 'gsp',
    'http://www.opengis.net/ont/gml': 'gml',
    'http://www.opengis.net/ont/sf#': 'sf',
    'http://www.opmw.org/ontology/': 'opmw',
    'http://www.ordnancesurvey.co.uk/ontology/Topography/v0.1/Topography.owl#': 'ostop',
    'http://www.samos.gr/ontologies/helpdeskOnto.owl#': 'hdo',
    'http://www.semanticdesktop.org/ontologies/2007/01/19/nie': 'nie',
    'http://www.semanticdesktop.org/ontologies/2007/03/22/nco#': 'nco',
    'http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#': 'nfo',
    'http://www.semanticdesktop.org/ontologies/2007/04/02/ncal#': 'ncal',
    'http://www.semanticdesktop.org/ontologies/2007/08/15/nao': 'nao',
    'http://www.semanticdesktop.org/ontologies/2007/08/15/nrl': 'nrl',
    'http://www.semanticweb.org/ontologies/2008/11/OntologySecurity.owl#': 'ontosec',
    'http://www.sensormeasurement.appspot.com/ont/transport/traffic': 'traffic',
    'http://www.tele.pw.edu.pl/~sims-onto/ConnectivityType.owl#': 'ct',
    'http://www.telegraphis.net/ontology/geography/geography#': 'geos',
    'http://www.telegraphis.net/ontology/measurement/measurement#': 'msr',
    'http://www.telegraphis.net/ontology/measurement/quantity#': 'quty',
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf',
    'http://www.w3.org/1999/xhtml/vocab': 'xhv',
    'http://www.w3.org/2000/01/rdf-schema#': 'rdfs',
    'http://www.w3.org/2000/10/swap/log#': 'log',
    'http://www.w3.org/2000/10/swap/pim/contact#': 'con',
    'http://acm.rkbexplorer.com/ontologies/acm#': 'acm',
    'http://aims.fao.org/aos/geopolitical.owl': 'geop',
    'http://www.w3.org/2000/10/swap/pim/doc#': 'doc',
    'http://www.w3.org/2001/02pd/rec54#': 'rec54',
    'http://www.w3.org/2001/sw/hcls/ns/transmed/': 'tmo',
    'http://www.w3.org/2002/07/owl': 'owl',
    'http://www.w3.org/2002/12/cal/ical': 'cal',
    'http://www.w3.org/2003/01/geo/wgs84_pos': 'geo',
    'http://www.w3.org/2003/06/sw-vocab-status/ns': 'vs',
    'http://www.w3.org/2003/11/swrl': 'swrl',
    'http://www.w3.org/2003/12/exif/ns': 'exif',
    'http://www.w3.org/2003/g/data-view': 'grddl',
    'http://www.w3.org/2004/02/skos/core': 'skos',
    'http://www.w3.org/2004/03/trix/rdfg-1/': 'rdfg',
    'http://www.w3.org/2004/03/trix/swp-1/': 'swp',
    'http://archivi.ibc.regione.emilia-romagna.it/ontology/eac-cpf/': 'eac-cpf',
    'http://bblfish.net/work/atom-owl/2006-06-06/': 'awol',
    'http://bibframe.org/vocab': 'bf',
    'http://code-research.eu/ontology/visual-analytics#': 'va',
    'http://commontag.org/ns#': 'ctag',
    'http://contextus.net/ontology/ontomedia/core/expression': 'oc',
    'http://contextus.net/ontology/ontomedia/core/space#': 'osr',
    'http://contextus.net/ontology/ontomedia/ext/common/being#': 'being',
    'http://contextus.net/ontology/ontomedia/ext/common/trait#': 'trait',
    'http://contextus.net/ontology/ontomedia/misc/date#': 'date',
    'http://courseware.rkbexplorer.com/ontologies/courseware#': 'crsw',
    'http://creativecommons.org/ns': 'cc',
    'http://www.w3.org/2004/09/fresnel': 'fresnel',
    'http://www.w3.org/2006/03/test-description': 'test',
    'http://www.w3.org/2006/gen/ont#': 'gso',
    'http://www.w3.org/2006/time': 'time',
    'http://d-nb.info/standards/elementset/agrelon.owl#': 'agrelon',
    'http://d-nb.info/standards/elementset/gnd': 'gndo',
    'http://data.archiveshub.ac.uk/def/': 'locah',
    'http://data.ign.fr/def/geofla': 'geofla',
    'http://data.ign.fr/def/geometrie#': 'geom',
    'http://data.ign.fr/def/ignf#': 'ignf',
    'http://data.ign.fr/def/topo#': 'topo',
    'http://data.lirmm.fr/ontologies/food': 'food',
    'http://data.lirmm.fr/ontologies/oan/': 'oan',
    'http://data.lirmm.fr/ontologies/osp#': 'osp',
    'http://data.lirmm.fr/ontologies/passim#': 'passim',
    'http://data.lirmm.fr/ontologies/poste#': 'poste',
    'http://data.lirmm.fr/ontologies/vdpp#': 'vdpp',
    'http://data.ordnancesurvey.co.uk/ontology/50kGazetteer/': 'g50k',
    'http://data.ordnancesurvey.co.uk/ontology/admingeo/': 'osadm',
    'http://data.ordnancesurvey.co.uk/ontology/geometry/': 'osgeom',
    'http://data.ordnancesurvey.co.uk/ontology/postcode/': 'postcode',
    'http://data.ordnancesurvey.co.uk/ontology/spatialrelations/': 'osspr',
    'http://data.press.net/ontology/asset/': 'pna',
    'http://data.press.net/ontology/classification/': 'pnc',
    'http://data.press.net/ontology/event/': 'pne',
    'http://data.press.net/ontology/identifier/': 'pni',
    'http://data.press.net/ontology/stuff/': 'pns',
    'http://data.press.net/ontology/tag/': 'pnt',
    'http://data.semanticweb.org/ns/swc/ontology': 'swc',
    'http://data.totl.net/game/': 'game',
    'http://dati.camera.it/ocd/': 'ocd',
    'http://def.seegrid.csiro.au/isotc211/iso19103/2005/basic': 'basic',
    'http://def.seegrid.csiro.au/isotc211/iso19107/2003/geometry#': 'gm',
    'http://def.seegrid.csiro.au/isotc211/iso19108/2002/temporal': 'tm',
    'http://def.seegrid.csiro.au/isotc211/iso19109/2005/feature#': 'gf',
    'http://def.seegrid.csiro.au/isotc211/iso19115/2003/dataquality#': 'dq',
    'http://def.seegrid.csiro.au/isotc211/iso19115/2003/extent#': 'ext',
    'http://def.seegrid.csiro.au/isotc211/iso19115/2003/lineage#': 'li',
    'http://def.seegrid.csiro.au/isotc211/iso19115/2003/metadata#': 'md',
    'http://def.seegrid.csiro.au/isotc211/iso19150/-2/2012/basic#': 'h2o',
    'http://def.seegrid.csiro.au/isotc211/iso19156/2011/observation': 'om',
    'http://def.seegrid.csiro.au/isotc211/iso19156/2011/sampling': 'sam',
    'http://dev.poderopedia.com/vocab/': 'poder',
    'http://elite.polito.it/ontologies/dogont': 'dogont',
    'http://environment.data.gov.au/def/op#': 'op',
    'http://eprints.org/ontology/': 'ep',
    'http://geovocab.org/geometry': 'ngeo',
    'http://geovocab.org/spatial': 'spatial',
    'http://id.loc.gov/vocabulary/relators/': 'mrel',
    'http://idi.fundacionctic.org/cruzar/turismo#': 'turismo',
    'http://iflastandards.info/ns/fr/frad/': 'frad',
    'http://iflastandards.info/ns/fr/frbr/frbrer/': 'frbrer',
    'http://inference-web.org/2.0/ds.owl#': 'dso',
    'http://inference-web.org/2.0/pml-provenance.owl#': 'pmlp',
    'http://iserve.kmi.open.ac.uk/ns/hrests#': 'hr',
    'http://iserve.kmi.open.ac.uk/ns/msm#': 'msm',
    'http://kdo.render-project.eu/kdo': 'kdo',
    'http://kmi.open.ac.uk/projects/smartproducts/ontologies/food.owl#': 'spfood',
    'http://labs.mondeca.com/vocab/endpointStatus': 'ends',
    'http://lemon-model.net/lemon': 'lemon',
    'http://lexvo.org/ontology': 'lvont',
    'http://linkedevents.org/ontology/': 'lode',
    'http://linkedgeodata.org/ontology/': 'lgdo',
    'http://linkedscience.org/lsc/ns#': 'lsc',
    'http://linkedscience.org/teach/ns': 'teach',
    'http://lod.taxonconcept.org/ontology/sci_people.owl#': 'scip',
    'http://lod.taxonconcept.org/ontology/txn.owl': 'txn',
    'http://lod.xdams.org/reload/oad/': 'oad',
    'http://loted.eu/ontology#': 'loted',
    'http://lsdis.cs.uga.edu/projects/semdis/opus': 'opus',
    'http://metadataregistry.org/uri/schema/RDARelationshipsGR2/': 'rdarel2',
    'http://moat-project.org/ns': 'moat',
    'http://ndl.go.jp/dcndl/terms/': 'dcndl',
    'http://ns.bergnet.org/tac/0.1/triple-access-control': 'tac',
    'http://ns.inria.fr/ast/sql': 'sql',
    'http://ns.inria.fr/emoca': 'emotion',
    'http://ns.inria.fr/nicetag/2010/09/09/voc': 'ntag',
    'http://ns.inria.fr/prissma/v1': 'prissma',
    'http://ns.inria.fr/s4ac/v2': 's4ac',
    'http://ns.nature.com/terms/': 'npg',
    'http://observedchange.com/moac/ns': 'moac',
    'http://observedchange.com/tisc/ns#': 'tisc',
    'http://ogp.me/ns#': 'og',
    'http://online-presence.net/opo/ns': 'opo',
    'http://ontologies.smile.deri.ie/pdo#': 'pdo',
    'http://ontology.it/itsmo/v1#': 'itsmo',
    'http://open-services.net/ns/asset#': 'am',
    'http://open-services.net/ns/core#': 'oslc',
    'http://open.vocab.org/terms/': 'ov',
    'http://openprovenance.org/model/opmo': 'opmo',
    'http://owlrep.eu01.aws.af.cm/fridge#': 'of',
    'http://paul.staroch.name/thesis/SmartHomeWeather.owl#': 'shw',
    'http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#': 'nif',
    'http://persistence.uni-leipzig.org/nlp2rdf/ontologies/rlog#': 'rlog',
    'http://privatealpha.com/ontology/certification/1': 'acrt',
    'http://purl.oclc.org/NET/ldr/ns': 'ldr',
    'http://purl.oclc.org/NET/muo/muo#': 'muo',
    'http://purl.oclc.org/NET/mvco.owl#': 'mvco',
    'http://purl.oclc.org/NET/ssnx/meteo/aws#': 'aws',
    'http://purl.oclc.org/NET/ssnx/qu/qu#': 'qu',
    'http://purl.oclc.org/NET/ssnx/ssn': 'ssn',
    'http://purl.org/LiMo/0.1': 'limoo',
    'http://purl.org/NET/biol/botany#': 'botany',
    'http://purl.org/NET/biol/ns': 'biol',
    'http://purl.org/NET/c4dm/event.owl': 'event',
    'http://purl.org/NET/c4dm/keys.owl': 'keys',
    'http://purl.org/NET/c4dm/timeline.owl': 'tl',
    'http://purl.org/NET/dady#': 'dady',
    'http://purl.org/NET/raul#': 'raul',
    'http://purl.org/NET/schema-org-csv#': 'scsv',
    'http://purl.org/NET/scovo': 'scovo',
    'http://purl.org/acco/ns': 'acco',
    'http://purl.org/archival/vocab/arch#': 'arch',
    'http://purl.org/b2bo#': 'b2bo',
    'http://purl.org/biodiversity/taxon/': 'taxon',
    'http://purl.org/biotop/biotop.owl': 'biotop',
    'http://purl.org/cerif/frapo/': 'frapo',
    'http://purl.org/cld/cdtype/': 'cdtype',
    'http://purl.org/cld/terms/': 'cld',
    'http://purl.org/co/': 'coll',
    'http://purl.org/configurationontology': 'cold',
    'http://purl.org/coo/ns': 'coo',
    'http://purl.org/ctic/dcat': 'dcat',
    'http://purl.org/ctic/empleo/oferta#': 'emp',
    'http://purl.org/ctic/infraestructuras/localizacion#': 'loc',
    'http://purl.org/ctic/infraestructuras/organizacion#': 'ctorg',
    'http://purl.org/ctic/sector-publico/elecciones#': 'elec',
    'http://purl.org/dc/dcam/': 'dcam',
    'http://purl.org/dc/dcmitype/': 'dctype',
    'http://purl.org/dc/elements/1.1/': 'dce',
    'http://purl.org/dc/terms/': 'dcterms',
    'http://purl.org/dqm-vocabulary/v1/dqm': 'dqm',
    'http://purl.org/dsnotify/vocab/eventset/': 'dsn',
    'http://purl.org/eis/vocab/daq#': 'daq',
    'http://purl.org/essglobal/vocab/v1.0/': 'essglobal',
    'http://purl.org/gen/0.1#': 'gen',
    'http://purl.org/goodrelations/v1': 'gr',
    'http://purl.org/healthcarevocab/v1': 'dicom',
    'http://purl.org/imbi/ru-meta.owl#': 'ru',
    'http://purl.org/innovation/ns': 'inno',
    'http://purl.org/iso25964/skos-thes#': 'iso-thes',
    'http://purl.org/library/': 'lib',
    'http://purl.org/limo-ontology/limo': 'limo',
    'http://purl.org/linguistics/gold/': 'gold',
    'http://purl.org/linked-data/api/vocab': 'api',
    'http://purl.org/linked-data/cube': 'qb',
    'http://purl.org/linked-data/sdmx': 'sdmx',
    'http://purl.org/linked-data/sdmx/2009/code': 'sdmx-code',
    'http://purl.org/linked-data/sdmx/2009/dimension': 'sdmx-dimension',
    'http://purl.org/linkingyou/': 'lyou',
    'http://purl.org/lobid/lv': 'lv',
    'http://purl.org/media#': 'media',
    'http://purl.org/muto/core': 'muto',
    'http://purl.org/net/lio#': 'lio',
    'http://purl.org/net/nknouf/ns/bibtex': 'bibtex',
    'http://purl.org/net/ns/ex': 'ex',
    'http://purl.org/net/ns/ontology-annot': 'ont',
    'http://purl.org/net/opmv/ns': 'opmv',
    'http://purl.org/net/p-plan': 'p-plan',
    'http://purl.org/net/po#': 'plo',
    'http://purl.org/net/provenance/ns': 'prv',
    'http://purl.org/net/provenance/types#': 'prvt',
    'http://purl.org/net/vocab/2004/03/label': 'label',
    'http://purl.org/net/wf-invocation#': 'wf-invoc',
    'http://purl.org/net/wf-motifs#': 'wfm',
    'http://purl.org/ontology/af/': 'af',
    'http://purl.org/ontology/ao/core': 'ao',
    'http://purl.org/ontology/bibo/': 'bibo',
    'http://purl.org/ontology/cco/core': 'cco',
    'http://purl.org/ontology/chord/': 'chord',
    'http://purl.org/ontology/co/core': 'co',
    'http://purl.org/ontology/daia/': 'daia',
    'http://purl.org/ontology/dso#': 'docso',
    'http://purl.org/ontology/dvia': 'dvia',
    'http://purl.org/ontology/is/core': 'is',
    'http://purl.org/ontology/mo/': 'mo',
    'http://purl.org/ontology/olo/core': 'olo',
    'http://purl.org/ontology/pbo/core': 'pbo',
    'http://purl.org/ontology/places#': 'place',
    'http://purl.org/ontology/po/': 'po',
    'http://purl.org/ontology/prv/core': 'prv',
    'http://purl.org/ontology/rec/core': 'rec',
    'http://purl.org/ontology/service#': 'service',
    'http://purl.org/ontology/similarity/': 'sim',
    'http://purl.org/ontology/ssso#': 'ssso',
    'http://purl.org/ontology/stories/': 'stories',
    'http://purl.org/ontology/storyline/': 'nsl',
    'http://purl.org/ontology/wi/core': 'wi',
    'http://purl.org/ontology/wo/': 'wlo',
    'http://purl.org/ontology/wo/core': 'wo',
    'http://purl.org/opdm/refrigerator#': 'ofrd',
    'http://purl.org/openorg/': 'oo',
    'http://purl.org/oslo/ns/localgov#': 'oslo',
    'http://purl.org/pav/': 'pav',
    'http://purl.org/procurement/public-contracts': 'pc',
    'http://purl.org/rss/1.0/': 'rss',
    'http://purl.org/saws/ontology': 'saws',
    'http://purl.org/spar/biro/': 'biro',
    'http://purl.org/spar/c4o/': 'c4o',
    'http://purl.org/spar/cito/': 'cito',
    'http://purl.org/spar/datacite/': 'dcite',
    'http://purl.org/spar/deo/': 'deo',
    'http://purl.org/spar/doco/': 'doco',
    'http://purl.org/spar/fabio/': 'fabio',
    'http://purl.org/spar/pro/': 'pro',
    'http://purl.org/spar/pso/': 'pso',
    'http://purl.org/spar/pwo/': 'pwo',
    'http://purl.org/spar/scoro/': 'scoro',
    'http://purl.org/stuff/rev#': 'rev',
    'http://purl.org/swan/2.0/discourse-relationships/': 'dr',
    'http://purl.org/theatre#': 'theatre',
    'http://purl.org/tio/ns': 'tio',
    'http://purl.org/twc/ontologies/cmo.owl': 'cmo',
    'http://purl.org/twc/ontology/cdm.owl#': 'cdm',
    'http://purl.org/twc/vocab/conversion/': 'conversion',
    'http://purl.org/uco/ns': 'uco',
    'http://purl.org/voc/vrank': 'vrank',
    'http://purl.org/vocab/aiiso/schema#': 'aiiso',
    'http://purl.org/vocab/bio/0.1/': 'bio',
    'http://purl.org/vocab/changeset/schema': 'cs',
    'http://purl.org/vocab/frbr/core': 'frbr',
    'http://purl.org/vocab/frbr/extended#': 'frbre',
    'http://purl.org/vocab/lifecycle/schema': 'lcy',
    'http://purl.org/vocab/participation/schema#': 'part',
    'http://purl.org/vocab/relationship/': 'rel',
    'http://purl.org/vocab/vann/': 'vann',
    'http://purl.org/vocommons/voaf#': 'voaf',
    'http://purl.org/vso/ns': 'vso',
    'http://purl.org/vvo/ns#': 'vvo',
    'http://purl.org/wai#': 'wai',
    'http://purl.uniprot.org/core/': 'uniprot',
    'http://qudt.org/schema/qudt': 'qudt',
    'http://rdf-vocabulary.ddialliance.org/discovery': 'disco',
    'http://rdf-vocabulary.ddialliance.org/phdd#': 'phdd',
    'http://rdf-vocabulary.ddialliance.org/xkos': 'xkos',
    'http://rdf.geospecies.org/methods/observationMethod#': 'obsm',
    'http://rdf.geospecies.org/ont/geospecies': 'geosp',
    'http://rdf.insee.fr/def/demo#': 'idemo',
    'http://rdf.insee.fr/def/geo#': 'igeo',
    'http://rdf.muninn-project.org/ontologies/appearances': 'aos',
    'http://rdf.muninn-project.org/ontologies/military': 'mil',
    'http://rdf.myexperiment.org/ontologies/base/': 'meb',
    'http://rdf.myexperiment.org/ontologies/snarm/': 'snarm',
    'http://rdfs.co/bevon/': 'bevon',
    'http://rdfs.org/ns/void': 'void',
    'http://rdfs.org/scot/ns': 'scot',
    'http://rdfs.org/sioc/ns': 'sioc',
    'http://rdfs.org/sioc/types#': 'tsioc',
    'http://rdfunit.aksw.org/ns/core#': 'ruto',
    'http://rdvocab.info/Elements/': 'rdag1',
    'http://rdvocab.info/ElementsGr2/': 'rdag2',
    'http://rdvocab.info/ElementsGr3/': 'rdag3',
    'http://rdvocab.info/RDARelationshipsWEMI/': 'rdarel',
    'http://rdvocab.info/roles/': 'rdarole',
    'http://rdvocab.info/uri/schema/FRBRentitiesRDA/': 'rdafrbr',
    'http://reegle.info/schema#': 'reegle',
    'http://reference.data.gov.uk/def/central-government/': 'cgov',
    'http://reference.data.gov.uk/def/intervals/': 'interval',
    'http://reference.data.gov.uk/def/organogram/': 'odv',
    'http://reference.data.gov.uk/def/parliament/': 'parl',
    'http://reference.data.gov.uk/def/payment': 'pay',
    'http://reference.data.gov/def/govdata/': 'gd',
    'http://resource.geosciml.org/ontology/timescale/gts#': 'gts',
    'http://resource.geosciml.org/ontology/timescale/thors#': 'thors',
    'http://rhizomik.net/ontologies/copyrightonto.owl': 'cro',
    'http://salt.semanticauthoring.org/ontologies/sao#': 'sao',
    'http://salt.semanticauthoring.org/ontologies/sdo#': 'sdo',
    'http://salt.semanticauthoring.org/ontologies/sro#': 'sro',
    'http://schema.org/': 'schema',
    'http://schema.theodi.org/odrs#': 'odrs',
    'http://schemas.talis.com/2005/address/schema#': 'ad',
    'http://schemas.talis.com/2005/dir/schema#': 'dir',
    'http://schemas.talis.com/2005/user/schema#': 'user',
    'http://securitytoolbox.appspot.com/MASO#': 'maso',
    'http://securitytoolbox.appspot.com/securityAlgorithms': 'algo',
    'http://securitytoolbox.appspot.com/securityMain#': 'security',
    'http://securitytoolbox.appspot.com/stac#': 'stac',
    'http://semanticscience.org/resource/': 'sio',
    'http://semanticweb.cs.vu.nl/2009/11/sem/': 'sem',
    'http://semweb.mmlab.be/ns/apps4X': 'apps4X',
    'http://semweb.mmlab.be/ns/odapps#': 'odapps',
    'http://semweb.mmlab.be/ns/oh#': 'oh',
    'http://sensormeasurement.appspot.com/ont/home/homeActivity': 'homeActivity',
    'http://simile.mit.edu/2003/10/ontologies/vraCore3#': 'vra',
    'http://sindice.com/vocab/search#': 'search',
    'http://spi-fm.uca.es/spdef/models/deployment/spcm/1.0#': 'spcm',
    'http://spi-fm.uca.es/spdef/models/deployment/swpm/1.0#': 'swpm',
    'http://spi-fm.uca.es/spdef/models/genericTools/itm/1.0#': 'itm',
    'http://spi-fm.uca.es/spdef/models/genericTools/vmm/1.0#': 'vmm',
    'http://spi-fm.uca.es/spdef/models/genericTools/wikim/1.0#': 'wikim',
    'http://spinrdf.org/sp': 'sp',
    'http://spinrdf.org/spin#': 'spin',
    'http://spitfire-project.eu/ontology/ns/': 'spt',
    'http://sw-portal.deri.org/ontologies/swportal#': 'swpo',
    'http://swrc.ontoware.org/ontology': 'swrc',
    'http://umbel.org/umbel': 'umbel',
    'http://uri4uri.net/vocab#': 'uri4uri',
    'http://usefulinc.com/ns/doap#': 'doap',
    'http://vivoweb.org/ontology/core#': 'vivo',
    'http://voag.linkedmodel.org/voag': 'voag',
    'http://vocab.data.gov/def/drm#': 'drm',
    'http://vocab.data.gov/def/fea#': 'fea',
    'http://vocab.deri.ie/br#': 'br',
    'http://vocab.deri.ie/c4n': 'c4n',
    'http://vocab.deri.ie/cogs#': 'cogs',
    'http://vocab.deri.ie/csp#': 'csp',
    'http://vocab.deri.ie/odapp#': 'odapp',
    'http://vocab.deri.ie/ppo': 'ppo',
    'http://vocab.deri.ie/tao#': 'tao',
    'http://vocab.getty.edu/ontology': 'gvp',
    'http://vocab.lenka.no/geo-deling#': 'geod',
    'http://vocab.org/transit/terms/': 'transit',
    'http://vocab.org/whisky/terms/': 'whisky',
    'http://vocab.resc.info/communication#': 'comm',
    'http://www.agls.gov.au/agls/terms/': 'agls',
    'http://www.aktors.org/ontology/portal': 'akt',
    'http://www.aktors.org/ontology/support#': 'akts',
    'http://www.bbc.co.uk/ontologies/bbc/': 'bbc',
    'http://www.bbc.co.uk/ontologies/cms/': 'bbccms',
    'http://www.bbc.co.uk/ontologies/coreconcepts/': 'bbccore',
    'http://www.bbc.co.uk/ontologies/creativework/': 'cwork',
    'http://www.bbc.co.uk/ontologies/provenance/': 'bbcprov',
    'http://www.bbc.co.uk/ontologies/sport/': 'sport',
    'http://www.biopax.org/release/biopax-level3.owl#': 'biopax',
    'http://www.bl.uk/schemas/bibliographic/blterms#': 'blt',
    'http://www.cidoc-crm.org/cidoc-crm/': 'crm',
    'http://www.daml.org/2001/09/countries/iso-3166-ont#': 'coun',
    'http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#': 'ebucore',
    'http://www.ebusiness-unibw.org/ontologies/consumerelectronics/v1#': 'ceo',
    'http://www.ecole.ensicaen.fr/~vincentj/owl/id.owl': 'identity',
    'http://www.essepuntato.it/2008/12/pattern#': 'pattern',
    'http://www.essepuntato.it/2012/04/tvc/': 'tvc',
    'http://www.essepuntato.it/2013/03/cito-functions#': 'citof',
    'http://www.essepuntato.it/2013/10/vagueness/': 'vag',
    'http://www.europeana.eu/schemas/edm/': 'edm',
    'http://www.geonames.org/ontology': 'gn',
    'http://www.gsi.dit.upm.es/ontologies/marl/ns': 'marl',
    'http://www.gsi.dit.upm.es/ontologies/onyx/ns': 'onyx',
    'http://www.holygoat.co.uk/owl/redwood/0.1/tags/': 'tag',
    'http://www.ics.forth.gr/isl/MarineTLO/v4/marinetlo.owl': 'mtlo',
    'http://www.ics.forth.gr/isl/VoIDWarehouse/VoID_Extension_Schema.owl': 'voidwh',
    'http://www.kanzaki.com/ns/music': 'music',
    'http://www.kanzaki.com/ns/whois': 'whois',
    'http://www.lexinfo.net/lmf': 'lmf',
    'http://www.lexinfo.net/ontology/2.0/lexinfo': 'lexinfo',
    'http://www.lingvoj.org/olca': 'olca',
    'http://www.lingvoj.org/ontology#': 'lingvo',
    'http://www.lingvoj.org/semio#': 'semio',
    'http://www.linkedmodel.org/schema/dtype#': 'dtype',
    'http://www.linkedmodel.org/schema/vaem#': 'vaem',
    'http://www.loc.gov/mads/rdf/v1': 'mads',
    'http://www.loc.gov/premis/rdf/v1': 'premis',
    'http://www.mindswap.org/2003/owl/geo/geoFeatures20040307.owl#': 'geof',
    'http://www.oegov.org/core/owl/cc#': 'oecc',
    'http://www.oegov.org/core/owl/gc': 'oegov',
    'http://www.ontologydesignpatterns.org/cp/owl/informationrealization.owl#': 'infor',
    'http://www.ontologydesignpatterns.org/cp/owl/participation.owl#': 'odpart',
    'http://www.ontologydesignpatterns.org/cp/owl/sequence.owl#': 'seq',
    'http://www.ontologydesignpatterns.org/cp/owl/situation.owl#': 'situ',
    'http://www.ontologydesignpatterns.org/cp/owl/timeindexedsituation.owl': 'tis',
    'http://www.ontologydesignpatterns.org/cp/owl/timeinterval.owl#': 'ti',
    'http://www.ontologydesignpatterns.org/ont/dul/DUL.owl': 'dul',
    'http://www.ontologydesignpatterns.org/ont/dul/IOLite.owl#': 'iol',
    'http://www.ontologydesignpatterns.org/ont/dul/ontopic.owl#': 'ontopic',
    'http://www.ontologydesignpatterns.org/ont/lmm/LMM_L1.owl#': 'lmm1',
    'http://www.ontologydesignpatterns.org/ont/lmm/LMM_L2.owl#': 'lmm2',
    'http://www.ontologydesignpatterns.org/ont/web/irw.owl': 'irw',
    'http://www.ontologydesignpatterns.org/schemas/cpannotationschema.owl#': 'cpa',
    'http://www.ontotext.com/proton/protonext#': 'pext',
    'http://www.ontotext.com/proton/protonkm': 'pkm',
    'http://www.ontotext.com/proton/protonsys#': 'psys',
    'http://www.w3.org/2006/vcard/ns': 'vcard',
    'http://www.w3.org/2007/05/powder-s': 'wdrs',
    'http://www.w3.org/TR/2003/PR-owl-guide-20031209/wine#': 'vin',
    'http://www.w3.org/ns/adms': 'adms',
    'http://www.w3.org/ns/auth/acl#': 'acl',
    'http://www.w3.org/ns/auth/cert': 'cert',
    'http://www.w3.org/ns/dcat': 'dcat',
    'http://www.w3.org/ns/earl': 'earl',
    'http://www.w3.org/ns/hydra/core': 'hydra',
    'http://www.w3.org/ns/ldp': 'ldp',
    'http://www.w3.org/ns/locn': 'locn',
    'http://www.w3.org/ns/ma-ont': 'ma',
    'http://www.w3.org/ns/oa': 'oa',
    'http://www.w3.org/ns/org': 'org',
    'http://www.w3.org/ns/person#': 'person',
    'http://www.w3.org/ns/prov': 'prov',
    'http://www.w3.org/ns/r2rml': 'rr',
    'http://www.w3.org/ns/radion#': 'radion',
    'http://www.w3.org/ns/regorg': 'rov',
    'http://www.w3.org/ns/ui#': 'ui',
    'http://www.wiwiss.fu-berlin.de/suhl/bizer/D2RQ/0.1': 'd2rq',
    'http://xmlns.com/wot/0.1/': 'wot',
    'http://zbw.eu/namespaces/zbw-extensions/': 'zbwext',
    'https://decision-ontology.googlecode.com/svn/trunk/decision.owl#': 'decision',
    'https://raw.githubusercontent.com/airs-linked-data/lov/latest/src/airs_vocabulary.ttl#': 'airs',
    'https://www.auto.tuwien.ac.at/downloads/thinkhome/ontology/WeatherOntology.owl': 'homeWeather',
    'http://xmlns.com/foaf/': 'foaf',
    'http://dbpedia.org/ontology/': 'dbpedia',
    'http://www.semanticdesktop.org/ontologies/2007/03/22/nfo': 'nfo',
    'http://linda-project.eu/ontology/ldao.owl': 'ldao',
    'https://github.com/dipapaspyros/FileSync/CloudStorageUnificationOntology': 'csuo',
    'http://linda.epu.ntua.gr/ontolygy/ppsonto': 'pps',
    # manually added
    'http://www.w3.org/2001/XMLSchema#': 'xmls',
    'http://dbpedia.org/resource/': 'dbpres' }


def get_mysql_cursor(db_host, db_user, db_password, db_database):
    connection = ''
    debug = True
    try:
        connection = mdb.connect(db_host, db_user, db_password, db_database);
        cursor = connection.cursor()
        return {'cursor':cursor, 'message':'ok', 'con': connection}
    except:
        logger.info("DB Connection failed:", )
        logger.info(sys.exc_info()[1])
        return {'cursor': None, 'message': sys.exc_info()[1], 'con': None}


def get_mysql_fkeys(cursor):
    erg = {}
    try:
        # foreign keys
        cursor.execute("SELECT k.TABLE_NAME, k.COLUMN_NAME, i.CONSTRAINT_TYPE, k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME \
             FROM information_schema.TABLE_CONSTRAINTS i LEFT JOIN information_schema.KEY_COLUMN_USAGE k ON i.CONSTRAINT_NAME = k.CONSTRAINT_NAME \
             WHERE i.CONSTRAINT_TYPE = 'FOREIGN KEY' AND i.TABLE_SCHEMA = DATABASE();")
        fkeys = cursor.fetchall()
        erg['fkeys'] = fkeys
        erg['error'] = None
        return erg
    except:
        logger.info("get_mysql_fkeys failed:", )
        logger.info(sys.exc_info()[1])
        erg['error'] = sys.exc_info()[1]
        return erg


def get_mysql_tables(cursor, fkeys):
    model = {}
    try:
        # tables
        table_list = []
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        for table in tables:
            table_list.append(get_mysql_table_data(cursor, table[0], fkeys, 10))
        model['tables'] = table_list
        
        # get relationship tables: 2 columns with foreign keys
#        set_mysql_f_keys(cursor, database, fkeys)
        for table in table_list:
            columns = table['columns']
            if len(columns) == 2:
                if columns[0]['foreign_key_string'] != "" and columns[1]['foreign_key_string'] != "":
                    table['isRelTable'] = "true"
                    table['handle_relTable'] = "true"
                else:
                    table['handle_relTable'] = "false"
            else:
                table['handle_relTable'] = "false"
        return {'model':model, 'message':'ok', 'error': None}
    except:
        logger.info("get_mysql_tables failed:", )
        logger.info(sys.exc_info()[1])
        return {'error': sys.exc_info()[1]}


def mysql_disconnect(con):
    con.close()
    return None


def get_mysql_table_data(cursor, table, fkeys, limit):
    res_table = {}
    debug = True
    try:
        if limit > 0:
            sql = "SELECT * FROM " + table + " LIMIT " + str(limit) + ";"
        else:
            sql = "SELECT * FROM " + table + ";"
        cursor.execute(sql)
        values_10 = cursor.fetchall()
        desc = cursor.description
        res_table =  {'name': table, 'selected': 'true'}
        values_10_l = [list(i) for i in values_10]
        values_10_ll = []
        for l in values_10_l:
            values_10_ll.append(['' if v is None else v for v in l])
        desc = cursor.description
        values_10_h = []
        for d in desc:
            values_10_h.append(d[0])
        values_10_ll.insert(0, values_10_h)
        res_table['values_10'] = values_10_ll
        cursor.execute("SHOW COLUMNS FROM " + table)
        fields = cursor.fetchall()
        desc = cursor.description
        schema_table_field_list = []
        for field in fields:
            has_fk = False
            for fkey in fkeys:
                if  table == fkey[0]:
                    if field[0] == fkey[1]:
                        b = fkey[3] + ":" +  fkey[4]
                        has_fk = True
            if not has_fk:
                b = ""
            new = {'name': field[0], 'type': field[1], 'hasNullValues': field[2], 'isPrimaryKey': field[3], 'foreign_key_string': b, 'selected': 'true'}
            schema_table_field_list.append(new)
        res_table['columns'] = schema_table_field_list
        cursor.execute("SELECT COUNT(*) FROM " + table)
        num_rows = cursor.fetchone()
        res_table['num_rows'] = num_rows[0]
        
        return res_table
    except: 
        logger.info(sys.exc_info()[1])
        logger.info("get_mysql_table_data failed:", )
        return None

        
def get_mysql_sql_table_data3(cursor, sql_query, sql_query_all):
    try:
        sql_table = {}
        cursor.execute(sql_query)
        values_10 = cursor.fetchall()
        values_10_l = [list(i) for i in values_10]
        values_10_ll = []
        for l in values_10_l:
            values_10_ll.append(['' if v is None else v for v in l])
        desc = cursor.description
        
        values_10_h = []
        for d in desc:
            values_10_h.append(d[0])
        values_10_ll.insert(0, values_10_h)
        sql_table['values_10_selected'] = values_10_ll
        
        
        cursor.execute(sql_query_all)
        values_10 = cursor.fetchall()
        values_10_l = [list(i) for i in values_10]
        values_10_ll = []
        for l in values_10_l:
            values_10_ll.append(['' if v is None else v for v in l])
        desc = cursor.description
        
        values_10_h = []
        for d in desc:
            values_10_h.append(d[0])
        values_10_ll.insert(0, values_10_h)
        sql_table['values_10'] = values_10_ll
    
        return sql_table
    except:
        logger.info("get_mysql_sql_table_data3 failed:", )
        logger.info(sys.exc_info()[1])
        return {'message': str(sys.exc_info()[1])}

        
def get_mysql_sql_table_data2(cursor, sql_name, sql_query, fkeys, limit):
    try:
        num_rows = 0
        if len(sql_name) == 0:
            return {'message': "Error: please provide a table name for the sql query."}
        sql_query = sql_query.split(';')[0]
        # SELECT
        match_select = re.search("^SELECT", sql_query, re.I)
        if match_select:
            sql_query_replaced = urlquote(sql_query)
#            sql_query_replaced = sql_query.replace("'", "\\\'")
#            sql_query_replaced = sql_query_replaced.replace('"', "\\\'")
#            logger.info(sql_query)
#            logger.info(sql_query_replaced)
            sql_table = {'sql_query': sql_query_replaced, 'selected': 'true'}
            sql_table['name'] = sql_name
            # LIMIT
            match_limit = re.search("LIMIT", sql_query, re.I)
            if match_limit == None:
                cursor.execute(sql_query)
                values = cursor.fetchall()
                num_rows = len(values)
                sql_query = sql_query.replace(";", " LIMIT " + str(limit) + ";")
            else:
                sql_query2 = sql_query[0 : match_limit.start(0)] + ";"
                cursor.execute(sql_query2)
                values = cursor.fetchall()
                num_rows = len(values)                
            cursor.execute(sql_query)
            values_10 = cursor.fetchall()
            sql_table['handle_relTable'] = 'false'
            values_10_l = [list(i) for i in values_10]
            values_10_ll = []
            for l in values_10_l:
                values_10_ll.append(['' if v is None else v for v in l])
            desc = cursor.description
            
            values_10_h = []
            for d in desc:
                values_10_h.append(d[0])
            values_10_ll.insert(0, values_10_h)
            sql_table['values_10'] = values_10_ll
            
            column_list = []
            for counter, field in enumerate(desc):
                column = {'name': field[0], 'type': field_type[field[1]], 'hasNullValues': field_null_allowed[field[6]], 'foreign_key_string': '', 'selected': 'true' }
                if not column in column_list:
                    column_list.append(column)
                else:
                    return {'message': 'Error: column-names have to be distinct.<br>Please change your SQL statement e.g. "<b>SELECT</b> student.Name <b>AS</b> Student_name ... "'}
            sql_table['columns'] =  column_list
            sql_table['num_rows'] = num_rows

            return sql_table
        else:
            return {'message': 'Error: ONLY SELECT statements are allowed in the sql-query'}
    except:
        logger.info("get_mysql_sql_table_data2 failed:", )
        logger.info(sys.exc_info()[1])
        return {'message': str(sys.exc_info()[1])}


# from transformation/static/js/common.js
# returns sth like 
# 'http.someurl.org/first_name'  -->  ['http.someurl.org/', 'first_name', 'some']
def replacePrefix(uri):
    result = {
        'url': uri,
        'suffix':'', 
        'prefix':'' }
    for key in lindaGlobals_prefixes: 
        if uri and uri.find(key) == 0 and uri.replace(key, "").find("#")==-1 and uri.replace(key, "").find("/")==-1:
            result['suffix'] = uri.replace(key, "")
            result['prefix'] = lindaGlobals_prefixes[key]
            result['url'] = key
            return result
    return result


def lookup(request, queryClass, queryString, callback):
    headers = {'Accept': 'application/json'}
    r = requests.get(
        'http://lookup.dbpedia.org/api/search/KeywordSearch?QueryClass=' + queryClass + '&QueryString=' + queryString,
        headers=headers)
    text = r.text
    results = json.loads(text)
    return callback + "(" + JsonResponse(results) + ");"


def lookup2(queryClass, queryString):
#    logger.info("lookup::queryString: ")
#    logger.info(queryString)
    headers = {'Accept': 'application/json'}
    try:
        result = requests.get('http://lookup.dbpedia.org/api/search/KeywordSearch?QueryString=' + queryString, headers=headers)
        return json.loads(result.text)
    except:
        logger.info("lookup2 failed:")
        return "error"
#    result = requests.get(
#        'http://lookup.dbpedia.org/api/search/KeywordSearch?QueryClass=' + queryClass + '&QueryString=' + queryString,
#        headers=headers)
#         http://lookup.dbpedia.org/api/search/KeywordSearch?QueryString=


def transformdb2n3(jsonmodel, request):
    empty_graph = True 
    tables = []
    if 'tables' in jsonmodel:
        tables = jsonmodel["tables"]
    prefixes = []
    if 'prefixes' in jsonmodel:
        prefixes = jsonmodel["prefixes"]
    output = ""
    for prefix in prefixes:
        output += "@prefix " + prefix["prefix"] + ":\t\t <" + prefix["url"] + "> .\n"
    pattern = re.compile('{.*?}')
    for table in tables:
        base_iri = ""
        if 'base_iri' in table:
            base_iri = table['base_iri']
            if base_iri == "/":
                base_iri = ""
        num_cols = len(table['columns'])
        num_selected_cols = 0
        selected_cols_list = []
        columns = table["columns"]
        for column in columns:
            if column['selected'] == "true":
                num_selected_cols += 1
                selected_cols_list.append(column['name'])
        subject_uri = ""
        if 'subject_uri' in table:
            subject_uri = table['subject_uri']
        if table['handle_relTable'] == "false":
            this_pk_list = []
            this_pk_list_c = []            
        while len(subject_uri) > 0:
            m = pattern.search(subject_uri)
            if m:
                pk_index = m.start()
                pk = m.group()
                this_pk_list_c.append(pk)
                pk = pk[1: len(pk)-1]
                this_pk_list.append(pk)
                substr_start = pk_index + len(pk) + 2
                subject_uri = subject_uri[substr_start: len(subject_uri)]
        if 'values_10_selected' in table:
            values_10_selected = table['values_10_selected']
        else:
            values_10_selected = []
        if len(values_10_selected) > 1: 
            empty_graph = False
        numrows = num_selected_cols * len(values_10_selected)
        obj_array = [];
#        if len(values_10_selected) >= 10: 
        if table['num_rows'] >= 10: 
            res = get_mysql_cursor(request.session['host'], request.session['user'],  request.session['password'], request.session['db'])
            cursor = res['cursor']
            fkeys = request.session['fkeys']            
            res2 = get_mysql_table_data(cursor, table['name'], fkeys, 0)
            values_10 = res2['values_10']
            mysql_disconnect(res['con'])
            
            row_head = values_10[0];

            values_10_selected = []
            values_10_selected.append(selected_cols_list)
            for j in range(1, len(values_10)):
                value_row = values_10[j]
                value_row_selected = []
                for k in range(0, len(row_head)):
                    col_name = row_head[k]
                    col_contains = False
                    column = getColumn(table, col_name)                  
                    for l in range(0, len(selected_cols_list)):
                        if col_name == selected_cols_list[l]:
                            col_contains = True
                    if col_contains:
                        if 'object_recons' in column and column['object_method'] != 'no action' :
#                        if 'object_recons' in column:
                            object_recons = column['object_recons']
                            if not(str(value_row[k]) in object_recons):
                                res = lookup2(col_name, str(value_row[k]))
                                if res != "error":
                                    res = res['results'][0]
                                    data = replacePrefix(res['uri'])
                                    if 'prefix' in data and data['prefix'] != "":
                                        # data {'suffix': 'Basketball', 'url': 'http://dbpedia.org/resource/', 'prefix': 'dbpres'}
                                        column['object_recons'][data['suffix']] = data
                                        value_row_selected.append(urlquote(value_row[k], safe = '/:'))
                                        has_new_prefix = True
                                        for prefix in prefixes:
                                            if prefix['url'] == data['url']:
                                                has_new_prefix = False
                                                break
                                        if has_new_prefix:
                                            output = "@prefix " + data['prefix'] + ":\t\t <" + data['url'] + "> .\n" + output
                                    else:
                                        value_row_selected.append("<" + urlquote(res['uri'], safe = '/:') + ">")
                                else:
                                    if value_row[k].startswith( 'http' ):
                                        value_row_selected.append("<" + urlquote(value_row[k], safe = '/:') + ">")
                                    else:
                                        value_row_selected.append(urlquote(value_row[k], safe = '/:'))
                            else:
                                object_recon = object_recons[str(value_row[k])]
                                value_row_selected.append(object_recon['prefix'] + ":" + object_recon['suffix'])
                        else:
                            if value_row[k].startswith( 'http' ):
                                value_row_selected.append("<" + urlquote(value_row[k], safe = '/:') + ">")
                            else:
                                value_row_selected.append(urlquote(value_row[k], safe = '/:'))
                values_10_selected.append(value_row_selected)
            table['values_10_selected'] = values_10_selected
            table['values_10'] = values_10

        for i in range(1, len(values_10_selected)):
            for j in range (0, num_selected_cols):
                obj_array.append(values_10_selected[i][j]);
        enrich_array = []
        if 'enrich' in table:
            enrich_array = table['enrich']
        firstrun = True
        j = 0
        k = 1
        res_counter = 0
        for i in range(0, len(obj_array)): # i++, j++
            subject_uri = ""
            if 'subject_uri' in table:
                subject_uri = table['subject_uri']
            isNull = False
            row = ""
            if j == num_selected_cols:
                j = 0
                k += 1
                firstrun = True
            selected_column = None
            for column in table['columns']:
                if column['name'] == selected_cols_list[j]:
                    selected_column = column
            
            if firstrun:
                for l in range(0, len(enrich_array)):
                    row = ""
                    prefix = enrich_array[l]['prefix']
                    if table['handle_relTable'] == "false":
                        subject_str = base_iri;
                        for ii in range(0, len(this_pk_list)):
                            for jj in range(0, num_selected_cols):
                                if this_pk_list[ii] == table['columns'][jj]['name']:
                                    subject_uri = subject_uri.replace(this_pk_list_c[ii], str(table['values_10'][k][jj]))
                        if len(base_iri) > 0:
                            subject_str = "<" + urlquote(subject_str + subject_uri, safe = '/:') + ">"
                        else:
                            subject_str = "_" + table['name'] + ":" + subject_uri;
                        row += subject_str + "\t"
                    else:
                        foreign_key_string_0 = columns[0]["foreign_key_string"]
                        foreign_key_string_arr_0 = re.split(':', foreign_key_string_0)
                        target_table_0_name = foreign_key_string_arr_0[0]
                        foreign_key_string_1 = columns[1]["foreign_key_string"]
                        foreign_key_string_arr_1 = re.split(':', foreign_key_string_1)
                        target_table_1_name = foreign_key_string_arr_1[0]
                        target_table_0 = getTable(jsonmodel, target_table_0_name)
                        target_table_1 = getTable(jsonmodel, target_table_1_name)
                        targetColumn_0 = getColumn(target_table_0, foreign_key_string_arr_0[1])
                        targetColumn_1 = getColumn(target_table_1, foreign_key_string_arr_1[1])
                        
                        if selected_column['name'] == targetColumn_0['name'] and targetColumn_0['selected'] == 'true':
                            if len(target_table_0['base_iri']) > 0:
                                new_val = "<" + target_table_0['base_iri'] + target_table_0['subject_uri'] + ">\t"
                            else:
                                new_val = "_" + target_table_0_name + ":"  + target_table_0['subject_uri'] + "\t"
                            res = getRelVal(table, selected_column['name'], obj_array[i], res_counter)
                            res_counter = res['i']
                            new_val = new_val.replace("{" + foreign_key_string_arr_0[1] + "}", res['new_val']);
                            row += new_val
                        if selected_column['name'] == targetColumn_1['name'] and targetColumn_1['selected'] == 'true':
                            if len(target_table_1['base_iri']) > 0:
                                new_val = "<" + target_table_1['base_iri'] + target_table_1['subject_uri'] + ">\t"
                            else:
                                new_val = "_" + target_table_1_name + ":"  + target_table_1['subject_uri'] + "\t"
                            res = getRelVal(table, selected_column['name'], obj_array[i], res_counter)
                            res_counter = res['i']
                            new_val = new_val.replace("{" + foreign_key_string_arr_1[1] + "}", res['new_val']);
                            row += new_val
                    row += "rdf:type\t" 
                    if prefix['prefix'] != "":
                        row += prefix['prefix'] + ":" + prefix['suffix'] + "\t .\n"
                    else :
                        row += "<" + prefix['url'] + ">\t .\n"
                    output += row
            firstrun = False
            
            for rdf_predicate in selected_column['rdf_predicate']:
                row = ""
                subject_str = base_iri;
            
                for ii in range(0, len(this_pk_list)):
                    for jj in range(0, num_selected_cols):
                        if this_pk_list[ii] == table['columns'][jj]['name']:
                            subject_uri = subject_uri.replace(this_pk_list_c[ii], str(table['values_10'][k][jj]))
                
                if table['handle_relTable'] == "false":
                    if len(base_iri) > 0:
                        subject_str = "<" + urlquote(subject_str + subject_uri, safe = '/:') + ">"
                    else:
                        subject_str = "_" + table['name'] + ":"  + subject_uri;
                    row += subject_str + "\t"
                else:
                    foreign_key_string_0 = columns[0]["foreign_key_string"]
                    foreign_key_string_arr_0 = re.split(':', foreign_key_string_0)
                    target_table_0_name = foreign_key_string_arr_0[0]
                    foreign_key_string_1 = columns[1]["foreign_key_string"]
                    foreign_key_string_arr_1 = re.split(':', foreign_key_string_1)
                    target_table_1_name = foreign_key_string_arr_1[0]
                    target_table_0 = getTable(jsonmodel, target_table_0_name)
                    target_table_1 = getTable(jsonmodel, target_table_1_name)
                    targetColumn_0 = getColumn(target_table_0, foreign_key_string_arr_0[1])
                    targetColumn_1 = getColumn(target_table_1, foreign_key_string_arr_1[1])

                    if selected_column['foreign_key_string'] == foreign_key_string_0:
                        if len(target_table_1['base_iri']) > 0:
                            new_val = "<" + target_table_1['base_iri'] + target_table_1['subject_uri'] + ">\t"
                        else:
                            new_val = "_" + target_table_1_name + ":" + target_table_1['subject_uri'] + "\t"
                        res = getRelVal(table, selected_column['name'], obj_array[i], res_counter)
                        res_counter = res['i']
                        new_val = new_val.replace("{" + foreign_key_string_arr_1[1] + "}", res['new_val'])
                        row += new_val
                    if selected_column['foreign_key_string'] == foreign_key_string_1:
                        if len(target_table_0['base_iri']) > 0:
                            new_val = "<" + target_table_0['base_iri'] + target_table_0['subject_uri'] + ">\t";
                        else:
                            new_val = "_" + target_table_0_name + ":" + target_table_0['subject_uri'] + "\t";
                        res = getRelVal(table, selected_column['name'], obj_array[i], res_counter)
                        res_counter = res['i']
                        new_val = new_val.replace("{" + foreign_key_string_arr_0[1] + "}", res['new_val']);
                        row += new_val

                row += rdf_predicate + "\t"
                if obj_array[i] == 'None' or obj_array[i] == "":
                    isNull = True
                # data type
                if 'data_type' in selected_column and selected_column['data_type'] != "":
                    new_pre = True
                    for ii in range(0, len(prefixes)):
                        pre = prefixes[ii];
                        if pre['prefix'] == selected_column['data_type']['prefix']:
                            new_pre = False
                    if new_pre:
                        new_pre = {'prefix': selected_column['data_type']['prefix'], 'url':selected_column['data_type']['url']};
                        prefixes.append(new_pre)
                    row += "\"" + str(obj_array[i]) + "^^" + selected_column['data_type']['prefix'] + ":" + selected_column['data_type']['suffix'] + "\"\t .\n"
                else:
                    # reconciliation
                    recon = get_model_reconciliation(jsonmodel, table['name'], selected_cols_list[j], obj_array[i])
                    if recon:
                        row += recon['prefix'] + ":" + recon['suffix'] + "\t . \n"
                    else:
                        if 'foreign_key_string' in selected_column and selected_column['foreign_key_string'] != "":
                            foreign_key_string = selected_column['foreign_key_string']
                            t_table  = foreign_key_string.split(":")[0]
                            t_column = foreign_key_string.split(":")[1]
                            targetTable = getTable(jsonmodel, t_table)
                            targetColumn = getColumn(targetTable, t_column)
                            if len(targetTable['base_iri']) > 0:
                                new_val = "<" + targetTable['base_iri'] + targetTable['subject_uri'] + ">\t . \n";
                            else:
                                new_val = "_" + targetTable['name'] + ":" + targetTable['subject_uri'] + "\t . \n";
                            new_val = new_val.replace("{" + t_column + "}", str(obj_array[i]));
                            row += new_val
                        else:
                            row += "\"" + str(obj_array[i]) + "\"\t . \n"
                if isNull == False:
                    output += row
            j += 1
    if empty_graph: 
        output = "# empty graph"
    return output


# res = getRelVal(table, selected_column['name'], obj_array[i], 0)    
def getRelVal(table, col_name, val, i):
    values_10 = table['values_10']
    if col_name == values_10[0][0]:
        col_source_index = 0
        col_result_index = 1
    else:
        col_source_index = 1
        col_result_index = 0
    for j in range(max(1, i), len(values_10)):
        row = values_10[j]        
        if row[col_source_index] == val:
            return {'i': j, 'new_val': str(row[col_result_index])}


def get_model_reconciliation(model, table_name, column_name, content_str):
    tables = []
    table = None
    column = None
    if 'tables' in model:
        tables = model["tables"]
    for table_ in tables:
        if table_['name'] == table_name:
            table = table_
    for column_ in table['columns']:
        if column_['name'] == column_name:
            column = column_

    if 'object_recons' in column and content_str in column['object_recons']:
        return column['object_recons'][content_str]
    else:
        return False


def transformdb2r2rml(jsonmodel):
    tables = []
    if 'tables' in jsonmodel:
        tables = jsonmodel["tables"]
    prefixes = []
    if 'prefixes' in jsonmodel:
        prefixes = jsonmodel["prefixes"]
    
    output = "@prefix rr:\t\t <http://www.w3.org/ns/r2rml#> .\n"
    for prefix in prefixes:
        output += "@prefix " + prefix["prefix"] + ":\t\t <" + prefix["url"] + "> .\n"

    table_counter = 1
    for table in tables:
        if table["selected"] == 'true':
            if table["handle_relTable"] == 'false':
                output += "\n<TriplesMap" + str(table_counter) + ">\n"
                output += "\ta rr:TriplesMap;\n"
                if 'sql_query' in table:
                     sql_query = parse.unquote(table['sql_query'])
                     output += "\n\trr:logicalTable [ rr:sqlQuery \"\"\"\n\t\t" + sql_query + "\n\t\t\"\"\"\n\t\t ];\n"
                else:
                    output += "\n\trr:logicalTable [ rr:tableName \"\\\"" + table["name"] + "\\\"\"; ] ;\n"
                output += "\n\trr:subjectMap [ \n"
                
                if table["base_iri"] == "":
                    output += "\t\trr:template \"" + table["subject_uri"].replace("{", "{\\\"").replace("}", "\\\"}\"") + "; rr:termType rr:BlankNode; \n";
                else:
                    output += "\t\trr:template \"" + table["base_iri"] + table["subject_uri"].replace("{", "{\\\"").replace("}", "\\\"}\"") + "\n";
                enriches = []
                if 'enrich' in table:
                    enriches = table["enrich"]
                for enrich in enriches:
                    prefix = enrich["prefix"]
                    if prefix["prefix"] != '' and prefix["suffix"] != '':
                        output += "\t\trr:class " + prefix["prefix"] + ":" + prefix["suffix"] + ";\n"
                    else:
                        output += "\t\trr:class <" + enrich["url"] + ">;\n"
                output += "\t];\n"
                columns = []
                sel_columns = []
                if 'columns' in table:
                    columns = table["columns"]
                for column in columns:
                    if column["selected"] == "true":
                        sel_columns.append(column)
                counter_sel_columns = 1
                for column in sel_columns:
#                    if column["selected"] == "true":
                    for rdf_predicate in column["rdf_predicate"]:
                        output += "\n\trr:predicateObjectMap\n"
                        output += "\t[\n"
                        output += "\t\trr:predicate\t " + rdf_predicate + " ;\n"
                        data_type = ""
                        if 'data_type' in column and 'prefix' in  column['data_type'] and 'suffix' in column['data_type']:
                            data_type = "rr:datatype " + column["data_type"]["prefix"] + ":" + column["data_type"]["suffix"]
                        if column["foreign_key_string"] == "":
                            output += "\t\trr:objectMap\t [ rr:column \"\\\"" + column["name"] + "\\\"\"; " + data_type + "] \n"
                        else:
                            foreign_key_string = column["foreign_key_string"]
                            foreign_key_string_arr = re.split(':', foreign_key_string)
                            target_table = foreign_key_string_arr[0]
                            target_column = foreign_key_string_arr[1]
                            output += "\t\trr:objectMap\t [ \n"
                            output += "\t\t\ta rr:RefObjectMap ; \n"                        
                            output += "\t\t\trr:parentTriplesMap <TriplesMap"+ getTableCounter(jsonmodel, target_table) +">;\n"
                            output += "\t\t\trr:joinCondition [\n"
                            output += "\t\t\t\trr:child \"\\\"" + column["name"] + "\\\"\" ;\n"
                            output += "\t\t\t\trr:parent \"\\\"" + target_column + "\\\"\" ; \n"
                            output += "\t\t\t] \n"
                            output += "\t\t]; \n"
                        if counter_sel_columns < len(sel_columns):
                            output += "\t];\n"
                        else:
                            output += "\t]\n\t.\n"
                    counter_sel_columns += 1
                        
            else: # relTable 
                columns = []
                if 'columns' in table:
                    columns = table["columns"]
                foreign_key_string_0 = columns[0]["foreign_key_string"]
                foreign_key_string_arr_0 = re.split(':', foreign_key_string_0)
                target_table_0_name = foreign_key_string_arr_0[0]
                foreign_key_string_1 = columns[1]["foreign_key_string"]
                foreign_key_string_arr_1 = re.split(':', foreign_key_string_1)
                target_table_1_name = foreign_key_string_arr_1[0]
                target_table_0 = getTable(jsonmodel, target_table_0_name)
                target_table_1 = getTable(jsonmodel, target_table_1_name)
#                <LinkMap_1_2>
                if columns[0]["selected"] == "true":
                    output += "\n<LinkMap_" + getTableCounter(jsonmodel, target_table_0_name) + "_" + getTableCounter(jsonmodel, target_table_1_name) + ">\n"
                    output += "\ta rr:TriplesMap;\n"
                    output += "\n\trr:logicalTable [ rr:tableName \"\\\"" + table["name"] + "\\\"\"; ] ;\n"
                    output += "\n\trr:subjectMap [ \n"
                    output += "\t\trr:template \"" + target_table_0["base_iri"] + "{\"" + columns[0]["name"] + "\"}\n";                    
                    enriches = []
                    if 'enrich' in table:
                        enriches = table["enrich"]
                    for enrich in enriches:
                        prefix = enrich["prefix"]
                        if prefix["prefix"] != '' and prefix["suffix"] != '':
                            output += "\t\trr:class " + prefix["prefix"] + ":" + prefix["suffix"] + ";\n"
                        else:
                            output += "\t\trr:class " + enrich["url"] + ";\n"
                    output += "\t];\n"
                    for rdf_predicate in columns[0]["rdf_predicate"]:
                        output += "\n\trr:predicateObjectMap\n"
                        output += "\t[\n"
                        output += "\t\trr:predicate\t " + rdf_predicate + " ;\n"
                        output += "\t\trr:objectMap	[ rr:template \"" + target_table_1["base_iri"] + "{\"" + columns[1]["name"] + "\"}\"];\n";
                        output += "\t];\n"
                    output += "\t.\n"
                if columns[1]["selected"] == "true":
                    output += "\n<LinkMap_" + getTableCounter(jsonmodel, target_table_1_name) + "_" + getTableCounter(jsonmodel, target_table_0_name) + ">\n"
                    output += "\ta rr:TriplesMap;\n"
                    output += "\n\trr:logicalTable [ rr:tableName \"\\\"" + table["name"] + "\\\"\"; ] ;\n"
                    output += "\n\trr:subjectMap [ \n"
                    output += "\t\trr:template \"" + target_table_1["base_iri"] + "{\"" + columns[1]["name"] + "\"}\n";
                    enriches = []
                    if 'enrich' in table:
                        enriches = table["enrich"]
                    for enrich in enriches:
                        prefix = enrich["prefix"]
                        if prefix["prefix"] != '' and prefix["suffix"] != '':
                            output += "\t\trr:class " + prefix["prefix"] + ":" + prefix["suffix"] + ";\n"
                        else:
                            output += "\t\trr:class <" + enrich["url"] + ">;\n"
                    output += "\t];\n"
                    for rdf_predicate in columns[1]["rdf_predicate"]:
                        output += "\n\trr:predicateObjectMap\n"
                        output += "\t[\n"
                        output += "\t\trr:predicate\t " + rdf_predicate + " ;\n"
                        output += "\t\trr:objectMap	[ rr:template \"" + target_table_0["base_iri"] + "{\"" + columns[0]["name"] + "\"}\"];\n";
                        output += "\t];\n"
                    output += "\t.\n"
        table_counter += 1
    return output


def getTable(jsonmodel, table_name):
    tables = jsonmodel["tables"]
    for table in tables:
        if table["selected"] == 'true':
            if table["name"] == table_name:
                return table
    return None
  

def getColumn(table, column_name):
    columns = table["columns"]
    for column in columns:
        if column["name"] == column_name:
            return column
    return None


def getTableCounter(jsonmodel, target_table):
    tables = jsonmodel["tables"]
    table_counter = 1
    for table in tables:
        if table["selected"] == 'true':
            if table["name"] == target_table:
                return str(table_counter)
            table_counter += 1
    return str(table_counter)

    
    
# ###############################################
#########       END RDB                ##########
# ###############################################
