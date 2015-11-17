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

    delete_unused_tmp_files()

    form = DataChoiceForm()
    mappings = Mapping.objects.filter(user=request.user.id)
    return render_to_response('transformation/data_choice.html', {'form': form, 'mappings': mappings},
                              context_instance=RequestContext(request))


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
#  OTHER FUNCTIONS
# ###############################################

def model_light(model):
    m2 = model.copy()
    del m2['object_recons']
    del m2['excerpt']
    del m2['file_name']
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

    if str(column) not in model['object_recons']:
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
    if skeleton != "" and base_url != "":
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

 
