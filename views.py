import csv
from io import TextIOWrapper
from io import StringIO
import os
import json
from django.http import HttpResponse
from django.shortcuts import render, render_to_response
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

# ###############################################
# MODELS
# ###############################################


def user_test(request):
    return render_to_response('transformation/user_test.html',
                              context_instance=RequestContext(request))


def data_choice(request):
    print("VIEW data_choice")
    # print(request.session)
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
    form = DataChoiceForm()
    mappings = Mapping.objects.filter(user=request.user.id)
    return render_to_response('transformation/data_choice.html', {'form': form, 'mappings': mappings},
                              context_instance=RequestContext(request))


def csv_upload(request):
    print("VIEW csv_upload")
    # save file

    form_action = 2
    publish_message = ""
    if request.method == 'POST':
        print("PATH 1 - POST")
        # a raw representation of the CSV file is also kept as we want to be able to change the CSV dialect and then reload the page
        csv_raw = None
        csv_rows = None
        csv_dialect = None
        upload_file_name = 'no file selected'

        # when an upload file was selected in html form, APPLY BUTTON
        if not request.FILES:
            form = UploadFileForm(request.POST)
            if request.POST and form.is_valid() and form is not None:
                print("PATH 1.1 - no file uploaded")
                # content is passed on via hidden html input fields
                if 'save_path' in request.session:
                    csv_rows, csv_dialect = process_csv(open(request.session['save_path'], "r"), form)
                else:
                    print('no raw csv')

                upload_file_name = form.cleaned_data['hidden_filename_field']

            # if page is loaded without POST
            else:
                print("PATH 1.2")

        # when file was uploaded
        else:  # if request.FILES:
            print("PATH 3 - file was uploaded")

            form = UploadFileForm(request.POST, request.FILES)
            upload_file_name = request.FILES['upload_file'].name
            upload_file = request.FILES['upload_file'].file

            # transformation of excel files to csv
            if upload_file_name[-4:] == "xlsx" or upload_file_name[-4:] == ".xls":
                # print(upload_file_name[-4:]);
                data_xls = pd.read_excel(request.FILES['upload_file'], 0, index_col=None)
                if not os.path.exists('tmp'):
                    os.makedirs('tmp')
                data_xls.to_csv('tmp/' + upload_file_name[:-4] + '.csv', encoding='utf-8')
                upload_file = open('tmp/' + upload_file_name[:-4] + '.csv', "rb")
                upload_file_name = upload_file_name[:-4] + '.csv'



            # file to array

            csv_rows = []
            csvLines = []
            rows = []
            csv_dialect = {}
            csv_raw = ""

            # read/process the CSV file and find out about its dialect (csv params such as delimiter, line end...)
            # https://docs.python.org/2/library/csv.html#
            print("endoding ", request.encoding)
            with TextIOWrapper(upload_file, encoding=request.encoding) as csv_file:
                # with TextIOWrapper(upload_file, encoding='utf-8') as csvfile:
                # the file is also provided in raw formatting, so users can appy changes (choose csv params) without reloading file 
                csv_raw = csv_file.read()
                 # TODO only one upload function!
                csv_rows, csv_dialect = process_csv(csv_file, form)

                # check if file is correct
                publish_message = '<span class="trafo_green"><i class="fa fa-check-circle"></i> File seems to be okay.</span>'
                num_last_row = len(csv_rows[0])
                for i in range(1, len(csv_rows)):
                    if len(csv_rows[i]) != num_last_row:
                        print("File seems to be either corrupted or it was loaded with wrong parameters!")
                        publish_message = '<span class="trafo_red"><i class="fa fa-exclamation-circle"></i> File seems to be corrupt or loaded with wrong parameters!</span>'
                        break

                # save file
                save_path = "filesaves/"
                session_id = request.session.session_key
                if request.user.is_authenticated():
                    print('user authenticated', request.user)
                    save_path += str(request.user)
                else:
                    print('user NOT authenticated: ', session_id)
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

                request.session['csv_dialect'] = csv_dialect
                request.session['csv_rows'] = csv_rows
                request.session['csv_raw'] = csv_raw

        if 'button_upload' in request.POST:
            print("UPLOAD BUTTON PRESSED")
            csv_rows = csv_rows if csv_rows else None

            request.session['csv_dialect'] = csv_dialect
            request.session['csv_rows'] = csv_rows
            #request.session['csv_raw'] = csv_raw
            if 'upload_file' in request.FILES:
                request.session['file_name'] = request.FILES['upload_file'].name
            # return redirect(reverse('csv-column-choice-view'))
            html_post_data = {
                'action': form_action,
                'form': form,
                'csvContent': request.session['csv_rows'][:11],
                #'csvRaw': request.session['csv_raw'],
                #'csvDialect': request.session['csv_dialect'],
                'filename': request.session['file_name'],
                'publish_message': publish_message
            }
            return render(request, 'transformation/csv_upload.html', html_post_data)

        if 'button_choose' in request.POST:
            # print(request.POST['mapping_id'])
            request.session['model'] = json.loads(
                Mapping.objects.filter(id=request.POST['mapping_id'])[0].mappingFile.read().decode("utf-8"))
            form = UploadFileForm()
            return render(request, 'transformation/csv_upload.html', {'action': 1, 'form': form})

    # html GET, we get here when loading the page 'for the first time'
    else:  # if request.method != 'POST':
        print("PATH 4 - initial page call (HTML GET)")
        form = UploadFileForm()
        return render(request, 'transformation/csv_upload.html', {'action': 1, 'form': form})


def csv_column_choice(request):
    print("VIEW csv_column_choice")
    form_action = 3
    reduced_model = None
    publish_message = None
    form = CsvColumnChoiceForm(request.POST)
    time1 = datetime.datetime.now()

    if 'model' not in request.session:
        print('creating model')

        arr = request.session['csv_rows']
        m = {"file_name": request.session['file_name'], "num_rows_total": len(arr)-1, "num_cols_selected": len(arr),
             "columns": [], "csv_dialect": request.session['csv_dialect'], "save_path": request.session['save_path']}
        f = -1
        c = -1

        try:

            for i, head in enumerate(arr[0]):
                m['columns'].append({'col_num_orig': i + 1, 'header': {'orig_val': arr[0][i]}})

            '''   
            for field in range(1, len(arr)):
                f = field
                for col in range(0, len(arr[field])):
                    c = col
                    m['columns'][col]['fields'].append({'orig_val': arr[field][col], 'field_num': field})
            '''
        except IndexError:
            print("index error: col " + str(c) + ", field " + str(f))


        # TODO uncomment
        update_excerpt(m, start_row=0, num_rows=10)


        request.session['model'] = m
        # print(request.session['model'])
        secs = datetime.datetime.now() - time1
        print("done " + str(secs))
        print_model_dim(request.session['model'])
        # print_fields(request.session['model'])

    # has fields? if not, only scaffolding from model 'loaded' in data choice page of wizard
    elif 'model' in request.session and 'excerpt' not in request.session['model']:
        # when only a loaded model 'scaffolding'
        print("model 'scaffolding' was loaded")



        # print("mod vor laden")
        # print_fields(request.session['model'])

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
                print("index error: col " + str(c) + ", field " + str(f))

        # csv_rows_selected_columns = get_selected_rows_content(request.session)
        # mark_selected_rows_in_model(request.session)

        # print("mod nach laden")
        # print_fields(request.session['model'])
        print_model_dim(request.session['model'])

    elif request.POST and form.is_valid() and 'hidden_model' in form.cleaned_data and form.cleaned_data['hidden_model']:
        print("model existing")
        reduced_model = json.loads(form.cleaned_data['hidden_model'])
        request.session['model'] = update_model(request.session['model'], reduced_model)
        #print_model_dim(request.session['model'])

    html_post_data = {
        'rdfModel': json.dumps(request.session['model']),
        'action': form_action,
        'csvContent': request.session['csv_rows'][:11],
        'filename': request.session['file_name'],
        'publish_message': publish_message
    }
    if 'model' in request.session and 'rdfModel' not in html_post_data:
        # print_fields(request.session['model'])
        print("reducing...")
        redu = reduce_model(request.session['model'], 10)
        # redu = reduced_model
        html_post_data['rdfModel'] = json.dumps(redu)
        # print_fields(redu)
        # html_post_data['rdfModel'] = request.session['model']
    # print("mod vor senden")
    # print_fields(request.session['model'])
    request.session.modified = True
    # print("mod vor senden 2")
    # print_fields(html_post_data['rdfModel'])
    return render(request, 'transformation/csv_column_choice.html', html_post_data)


def csv_subject(request):
    print("VIEW csv_subject")

    print("mod direkt nach laden seite")
    print(request.session['model'])

    print("-----")
    form_action = 4
    form = SubjectForm(request.POST)
    dump = None
    reduced_model = None
    if request.POST and form.is_valid() and form is not None:

        # content  is passed on via hidden html input fields

        request.session['model'] = json.loads(form.cleaned_data['hidden_model'])
        #reduced_model = json.loads(form.cleaned_data['hidden_model'])
        #dump = json.dumps(reduced_model)
        #print("dump   ", str(dump))
        '''
        if 'hidden_model' in form.cleaned_data:
            time1 = datetime.datetime.now()
            print("fetching model")
            print(form.cleaned_data['hidden_model'].index("file_name"))
            reduced_model = json.loads(form.cleaned_data['hidden_model'])
            print(reduced_model)
            print("red mod")
            print_fields(reduced_model)

            secs = datetime.datetime.now() - time1
            print("init: " + str(secs))
            time1 = datetime.datetime.now()

            if reduced_model:
                # request.session['model'] = update_model(request.session['model'], reduced_model)
                secs = datetime.datetime.now() - time1
                print("updating model: " + str(secs))
                time1 = datetime.datetime.now()
        '''

        update_excerpt(model=request.session['model'], start_row=0, num_rows=10)
    html_post_data = {
        'rdfModel': json.dumps(request.session['model']),
        'action': form_action,
        # 'csvContent': csv_rows_selected_columns,
        'filename': request.session['file_name'],
        # 'rdfArray': request.session['rdf_array'],
        # 'rdfPrefix': request.session['rdf_prefix']
    }
    return render(request, 'transformation/csv_subject.html', html_post_data)


def csv_predicate(request):
    print("VIEW csv_predicate")
    form_action = 5
    form = PredicateForm(request.POST)
    reduced_model = None
    if request.POST and form.is_valid() and form is not None:
        # content  is passed on via hidden html input fields
        '''
        if 'hidden_rdf_array_field' in form.cleaned_data:
            request.session['rdf_array'] = form.cleaned_data['hidden_rdf_array_field']

        if 'hidden_rdf_prefix_field' in form.cleaned_data:
            request.session['rdf_prefix'] = form.cleaned_data['hidden_rdf_prefix_field']
        '''
        if 'hidden_model' in form.cleaned_data:
            request.session['model'] = json.loads(form.cleaned_data['hidden_model'])
            update_excerpt(request.session['model'], start_row=0, num_rows=10)
            '''
            reduced_model = json.loads(form.cleaned_data['hidden_model'])

            request.session['model'] = reduced_model
            update_excerpt(request.session['model'], start_row=0, num_rows=10)

            time1 = datetime.datetime.now()
            request.session['model'] = update_model(request.session['model'], reduced_model)
            secs = datetime.datetime.now() - time1
            print("updating model: " + str(secs))
            '''

    # csv_rows_selected_columns = get_selected_rows_content(request.session)
    #time1 = datetime.datetime.now()
    #redu = reduce_model(request.session['model'], 10)
    # redu = reduced_model
    #secs = datetime.datetime.now() - time1
    #print("reducing model: " + str(secs))
    html_post_data = {
        'action': form_action,
        'rdfModel': json.dumps(request.session['model']),
        # 'csvContent': csv_rows_selected_columns,
        'filename': request.session['file_name'],
        # 'rdfArray': request.session['rdf_array'],
        # 'rdfPrefix': request.session['rdf_prefix']
    }
    return render(request, 'transformation/csv_predicate.html', html_post_data)


def csv_object(request):
    """
    """

    '''
    #TEST
    m1 = {'columns':[{'fields':[{'field_num':1,'c':'cccold'},{'field_num':4,'c':'ccc2'}]}]}
    print(">>>>>>>>>>")
    print(m1)
    m2red = {'columns':[{'fields':[{'field_num':1,'c':'cccnew'},{'field_num':3,'c':'cccverynew'}]}]}
    m1 = update_model(m1,m2red)
    print("<<<<<<<<<<")
    print(m1)
    print("<<<<<<<<<<")
    m2red = {'columns':[{'fields':[{'field_num':1,'c':'cccnew'},{'field_num':3,'c':'kkkkkkkkkkkkkkkkkk'}]}]}    
    print(m1)
    '''

    print("VIEW csv_object")
    form_action = 6
    form = ObjectForm(request.POST)
    reduced_model = None
    # print(request.POST)
    if request.POST and form.is_valid():  # and form != None:
        # content  is passed on via hidden html input fields
        '''
        if 'hidden_rdf_array_field' in form.cleaned_data:
            request.session['rdf_array'] = form.cleaned_data['hidden_rdf_array_field']

        if 'hidden_rdf_prefix_field' in form.cleaned_data:
            request.session['rdf_prefix'] = form.cleaned_data['hidden_rdf_prefix_field']
        '''
        if 'hidden_model' in form.cleaned_data:
            request.session['model'] = json.loads(form.cleaned_data['hidden_model'])            

        else:
            request.session['model'] = ""
            print("N O     M O D E L")
    else:
        print("form not valid!")

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

    # request.session['model'] = json.loads(form.cleaned_data['hidden_model'])
    # request.session['model'] =
    # print("v ",len(request.session['model']['columns'][1]['fields']))
    # print("v ",request.session['model']['columns'][1]['fields'])
    # print("r ",len(reduced_model['columns'][1]))
    # print("r ",reduced_model['columns'][1])
    # request.session['model'] = update_model(request.session['model'], reduced_model)
    # print("r ",len(reduced_model['columns'][1]['fields']))
    # print("r ",reduced_model['columns'][1]['fields'])
    # print("n ",len(request.session['model']['columns'][1]))
    # print("n ",request.session['model']['columns'][1])


    # csv_rows_selected_columns = get_selected_rows_content(request.session)
    html_post_data = {
        'pagination': pagination,
        'action': form_action,
        #'rdfModel': json.dumps(reduce_model(request.session['model'], pagination)),
        'rdfModel': json.dumps(request.session['model']),
        # 'rdfModel': json.dumps(reduced_model),
        # 'csvContent': csv_rows_selected_columns,
        'filename': request.session['file_name'],
        # 'rdfArray': request.session['rdf_array'],
        # 'rdfPrefix': request.session['rdf_prefix']
    }
    return render(request, 'transformation/csv_object.html', html_post_data)


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def csv_enrich(request):
    print("VIEW csv_additional")
    form_action = 7
    form = EnrichForm(request.POST)
    reduced_model = None
    if request.POST and form.is_valid() and form != None:
        # content  is passed on via hidden html input fields
        '''
        if 'hidden_rdf_array_field' in form.cleaned_data:
            request.session['rdf_array'] = form.cleaned_data['hidden_rdf_array_field']

        if 'hidden_rdf_prefix_field' in form.cleaned_data:
            request.session['rdf_prefix'] = form.cleaned_data['hidden_rdf_prefix_field']
        '''
        if 'hidden_model' in form.cleaned_data:
            #reduced_model = json.loads(form.cleaned_data['hidden_model'])
            #request.session['model'] = update_model(request.session['model'], reduced_model)
            request.session['model'] = json.loads(form.cleaned_data['hidden_model']) 
            update_excerpt(request.session['model'], start_row=0, num_rows=10)

    # csv_rows_selected_columns = get_selected_rows_content(request.session)
    html_post_data = {
        'action': form_action,
        'rdfModel': json.dumps(request.session['model']),
        # 'csvContent': csv_rows_selected_columns,
        'filename': request.session['file_name'],
        # 'rdfArray': request.session['rdf_array'],
        # 'rdfPrefix': request.session['rdf_prefix']
    }
    pass
    return render(request, 'transformation/csv_enrich.html', html_post_data)


def csv_publish(request):
    print("VIEW csv_publish")
    form_action = 7  # refers to itself
    form = PublishForm(request.POST)
    reduced_model = None
    publish_message = ""

    if request.POST and form.is_valid() and form != None:

        if 'hidden_model' in form.cleaned_data:
            #reduced_model = json.loads(form.cleaned_data['hidden_model'])
            #request.session['model'] = update_model(request.session['model'], reduced_model)
            request.session['model'] = json.loads(form.cleaned_data['hidden_model'])
            update_excerpt(request.session['model'], start_row=0, num_rows=10)

        if 'button_publish' in request.POST:
            payload = {'title': request.POST.get('name_publish'),
                       'content': model_to_triple_string(request.session['model']), 'format': 'text/rdf+n3'}
            # Please set the API_HOST in the settings file
            r = requests.post('http://' + API_HOST + '/api/datasource/create/', data=payload)
            j = json.loads(r.text)
            print(j["message"])
            publish_message = j["message"]

        if 'button_download' in request.POST:
            # TODO why does model lose file_name attr in subject view?
            # new_fname = request.session['model']['file_name'].rsplit(".", 1)[0] + ".n3"
            new_fname = request.session['file_name'].rsplit(".", 1)[0] + ".n3"
            rdf_string = model_to_triple_string(request.session['model'])
            rdf_file = ContentFile(rdf_string.encode('utf-8'))
            response = HttpResponse(rdf_file, 'application/force-download')
            response['Content-Length'] = rdf_file.size
            response['Content-Disposition'] = 'attachment; filename="' + new_fname + '"'
            # print(rdf_n3)
            return response

        if 'button_r2rml' in request.POST:
            # TODO why does model lose file_name attr in subject view?
            # new_fname = request.session['model']['file_name'].rsplit(".", 1)[0] + "_R2RML.ttl"
            new_fname = request.session['file_name'].rsplit(".", 1)[0] + "_R2RML.ttl"
            r2rml_string = transform_to_r2rml(request.session['model'])
            r2rml_file = ContentFile(r2rml_string.encode('utf-8'))
            response = HttpResponse(r2rml_file, 'application/force-download')
            response['Content-Length'] = r2rml_file.size
            response['Content-Disposition'] = 'attachment; filename="' + new_fname + '"'
            return response

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
        # 'rdfModel': json.dumps(request.session['model']),
        'rdfModel': json.dumps(request.session['model']),
        # 'csvContent': csv_rows_selected_columns,
        'filename': request.session['file_name'],
        # 'rdfArray': request.session['rdf_array'],
        # 'rdfPrefix': request.session['rdf_prefix']
    }
    return render(request, 'transformation/csv_publish.html', html_post_data)


# ###############################################
#  OTHER FUNCTIONS
# ###############################################


def model_light(model):
    """
    Delete all field and file specific data, that is keep only data that will be needed when loading csvs of the same structure but containing different content
    """
    result = copy.deepcopy(model)
    if 'file_name' in result:
        del result['file_name']
    for col in result['columns']:
        if 'fields' in col:
            del col['fields']
            # if 'header' in col:
            #    del col['header']
    return result


def lookup(request, queryClass, queryString, callback):
    headers = {'Accept': 'application/json'}
    r = requests.get(
        'http://lookup.dbpedia.org/api/search/KeywordSearch?QueryClass=' + queryClass + '&QueryString=' + queryString,
        headers=headers)
    text = r.text
    results = json.loads(text)
    return callback + "(" + JsonResponse(results) + ");"


# returns only the contents of the columns that were chosen in the html form from the session data
# for step 2 (column selection)
def get_selected_rows_content(session):
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


'''
# marks selected columns directly in model
def mark_selected_rows_in_model(session):
    # write column numbers in array
    col_nums = []
    print(session['selected_columns'])
    for col_num in session['selected_columns']:
        col_nums.append(col_num.get("col_num_orig"))
    session['model']['num_cols_selected'] = len(col_nums)
    counter = 1;
    for i, col in enumerate(session['model']['columns']):
        if col["col_num_orig"] in col_nums:
            col["col_num_new"] = counter
            counter = counter + 1
        else:
            col["col_num_new"] = -1
'''


def process_csv(csv_file, form):
    """
    Processes the CSV File and converts it to a 2dim array.
    Uses either the CSV parameters specified in the HTML form if those exist
    or the auto-detected params instead.
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
        print("Form invalid")
        return None


def transform_to_r2rml(model):
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


def update_model(model, reduced_model):
    """
    Takes a model and updates it with reduced model
    """
    # fields
    m = copy.deepcopy(model)
    for i, col in enumerate(m['columns']):
        exists = -1
        for j, field in enumerate(reduced_model['columns'][i]['fields']):

            # for performance when paginating
            if exists == -1:
                rnge = range(0, len(model['columns'][i]['fields']))
            else:
                rnge = chain(range(exists, len(model['columns'][i]['fields'])), range(0, exists))

            # fields
            # for k, col_red in enumerate(model['columns'][i]['fields']):
            for k in rnge:
                if reduced_model['columns'][i]['fields'][j]['field_num'] == m['columns'][i]['fields'][k]['field_num']:
                    m['columns'][i]['fields'][k] = reduced_model['columns'][i]['fields'][j].copy()
                    # print("OVERWRiTING ", m['columns'][i]['fields'][j], "  ",reduced_model['columns'][i]['fields'][k])
                    exists = k
                    break
            if exists == -1:
                m['columns'][i]['fields'].append(reduced_model['columns'][i]['fields'][j].copy())
                # print("ADDING")
            # sort
            new_list = sorted(m['columns'][i]['fields'].copy(), key=lambda k: k['field_num'])
            m['columns'][i]['fields'] = new_list

        # predicate
        if 'predicate' in reduced_model['columns'][i]:
            col['predicate'] = copy.deepcopy(reduced_model['columns'][i]['predicate'])

        # column choice
        if 'col_num_new' in reduced_model['columns'][i]:
            col['col_num_new'] = copy.deepcopy(reduced_model['columns'][i]['col_num_new'])

        # header
        if 'header' in reduced_model['columns'][i]:
            col['header'] = copy.deepcopy(reduced_model['columns'][i]['header'])

        # object_method
        if 'object_method' in reduced_model['columns'][i]:
            col['object_method'] = copy.deepcopy(reduced_model['columns'][i]['object_method'])

        # data_type
        if 'data_type' in reduced_model['columns'][i]:
            col['data_type'] = copy.deepcopy(reduced_model['columns'][i]['data_type'])

    # subject
    if 'subject' in reduced_model:
        m['subject'] = copy.deepcopy(reduced_model['subject'])

    # enrich
    if 'enrich' in reduced_model:
        m['enrich'] = copy.deepcopy(reduced_model['enrich'])

    # file_name
    if 'file_name' in reduced_model:
        m['file_name'] = copy.deepcopy(reduced_model['file_name'])

    return m


def reduce_model(model, pagination):
    """
    pagination can be 
    int number: first x elements will be selected
    dict of 'pagination', with page and perPage attributes as in views.py -> csv_object function
    """
    reduced_model = copy.deepcopy(model)

    p = False
    f = 0
    if isinstance(pagination, dict) and 'page' in pagination and 'perPage' in pagination:
        p = True
        f = (pagination['page'] - 1) * pagination['perPage']
        t = f + pagination['perPage']
    for i, col in enumerate(reduced_model['columns']):
        if 'col_num_new' not in col or col['col_num_new'] > -1:  # show column

            if 'fields' not in reduced_model['columns'][i]:
                print("no fields in column ", i)
            else:
                if p:
                    fields = reduced_model['columns'][i]['fields'][f:t].copy()
                elif isinstance(pagination, int):
                    fields = reduced_model['columns'][i]['fields'][:pagination].copy()
                else:
                    fields = reduced_model['columns'][i]['fields'].copy()

                reduced_model['columns'][i]['fields'] = fields

        else:  # remove columns that are not selected
            reduced_model['columns'][i]['fields'] = []
    return reduced_model


def print_fields(model):
    """
    for debugging purposes
    """
    for c in model['columns']:
        if 'fields' in c:
            print(str(len(c['fields'])), " FIELDS YES in ", c['header']['orig_val'])
        else:
            print("FIELDS NOO in ", c['header']['orig_val'])


def print_model_dim(model):
    """
    for debugging purposes
    """
    if 'columns' in model and 'fields' in model['columns']:
        print("model dim: ", len(model['columns']), " x ", len(model['columns'][0]['fields']))


def model_to_triple_string(model):
    rdf_n3 = ""
    rdf_array = model_to_triples(model)

    for row in rdf_array:  # ast.literal_eval(request.session['rdf_array']):#['rdf_array']:
        for elem in row:
            elem = elem.replace(",", "\\,");  # escape commas
            if elem[-1:] == ".":  # cut off as we had problems when uploading some uri like xyz_inc. with trailing dot
                elem = elem[:-1]
            rdf_n3 += elem + " "
        rdf_n3 += ".\n"

    return rdf_n3


def model_to_triples(model):
    #num_fields_in_row_rdf = len(model['columns'][0]['fields'])
    num_fields_in_row_rdf = model['num_rows_total']
    num_total_cols = 0

    # count
    for col in model['columns']:
        if col['col_num_new'] > - 1:
            num_total_cols += 1

    num_total_fields_rdf = num_fields_in_row_rdf * num_total_cols

    print_model_dim(model)
    # print(num_total_cols, " cols")

    skeleton = model['subject']['skeleton']
    base_url = model['subject']['base_url']

    subject = "<?subject>"
    if skeleton != "" and base_url != "":
        subject = "<" + base_url + skeleton + ">"

    # contains names that are needed for subject creation
    skeleton_array = re.findall("\{(.*?)\}", skeleton)
    # print("skel: ", skeleton_array)

    rdf_array = [[subject, "<?p>", "<?o>"] for x in range(0, num_total_fields_rdf)]

    # print("rdf array dim ",len(rdf_array)," x ",len(rdf_array[0]))

    prefix_dict = {}

    complete_array = file_to_array(model=model)['rows']
    print("gealden ", len(complete_array), " - ", len(complete_array[0]))

    # objects
    count1 = 0
    for i, col in enumerate(model['columns']):
        if col['col_num_new'] > - 1:
            count2 = count1
            add = ""
            if 'object_method' in col and col['object_method'] == "data type":
                add = "^^" + col['data_type']['prefix'] + ":" + col['data_type']['suffix']
                prefix_dict[col['data_type']['prefix']] = col['data_type']
            for j, field in enumerate(complete_array):
                elem = field[col['col_num_orig']-1]
                if 'object_method' in col and col['object_method'] == "reconciliation" and 'obj_recons' in col and str(j+1) in col['obj_recons']:
                    rdf_array[count2][2] = col['obj_recons'][str(j+1)]['prefix']['prefix']+":"+col['obj_recons'][str(j+1)]['prefix']['suffix']
                    xxx = str(col['obj_recons'][str(j+1)]['prefix']['prefix'])
                    prefix_dict[xxx] = col['obj_recons'][str(j+1)]['prefix']['url']
                else:
                    rdf_array[count2][2] = '"' + elem + '"' + add
                count2 += num_total_cols
            count1 += 1

    # subjects
    rowlength = model['num_rows_total']
    if 'blank_nodes' in model['subject'] and model['subject']['blank_nodes'] == "true":        
        for i, col in enumerate(model['columns']):
            counter = 0
            counter2 = 0
            if col['col_num_new'] > - 1:
                for row_num in range(0,rowlength):
                    for x in range(counter, counter + num_total_cols):
                        rdf_array[x][0] = "_:" + to_letters(counter2)
                    counter += num_total_cols
                    counter2 += 1
    else:
        for i, s in enumerate(skeleton_array):
            for col in model['columns']:
                counter = 0
                if col['col_num_new'] > - 1:
                    for row_num in range(0,rowlength):
                        field = complete_array[row_num][col['col_num_orig']-1]
                        for x in range(counter, counter + num_total_cols):
                            if col['header']['orig_val'] == s:
                                #TODO translate url into right format instead of only .replace(" ", "%20")
                                rdf_array[x][0] = rdf_array[x][0].replace("{" + s + "}", field.replace(" ", "%20"))
                        counter += num_total_cols


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
                prefix_dict[prefix] = url
            for x in range(0, num_fields_in_row_rdf):
                rdf_array[count1 + x * num_total_cols][1] = u
            count1 += 1

    # enrich
    enrich_array = []
    if 'enrich' in model:
        for enr in model['enrich']:
            if enr['prefix']['prefix'] == "" or enr['prefix']['suffix'] == "":
                enrich_array.append(["<subject?>", "a", "<" + enr['prefix']['url'] + ">"])
            else:
                enrich_array.append(["<subject?>", "a", enr['prefix']['prefix'] + ":" + enr['prefix']['suffix']])
                prefix_dict[enr['prefix']['prefix']] = enr['prefix']['url']

    enrichs_inserted = 0
    for n in range(num_total_cols - 1, len(rdf_array) + num_total_cols - 1, num_total_cols):
        for enr in enrich_array:
            x = n + enrichs_inserted + 1
            rdf_array.insert(x, enr.copy())
            rdf_array[x][0] = rdf_array[x - 1][0]
            enrichs_inserted += 1

    prefix_array = []
    for x in prefix_dict:
        x1 = prefix_dict[x]
        x2 = prefix_dict[str(x)]
        prefix_array.append(["@prefix", x + ":", "<" + str(prefix_dict[x]) + ">"])

    return prefix_array + rdf_array


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
    """
    if not model:
        print("no model!")
        return

    # check if calculation of new excerpt is needed
    if 'excerpt' in model and model['excerpt']['num_rows'] == num_rows and model['excerpt']['start_row'] == start_row:
        return model
    else:
        model['excerpt'] = file_to_array(model=model, start_row=start_row, num_rows=num_rows)


def file_to_array(request=None, model=None, start_row=0, num_rows=-1):
    """
    Either HTTP request containing 'save_path' and 'csv_dialect', or LinDA JSON model parameter must exist.
    Prefers model.
    :param request: HTTP request
    :param model: LinDA JSON model
    :param start_row:
    :param num_rows: if -1 then all is returned
    :return: a dict like: {'rows': csv_array, 'start_row': start_row, 'num_rows': num_rows, 'total_rows_num': row_count}
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
            print("model param for file_to_array function is invalid")
    elif request is not None:
        if 'save_path' in request.session and 'csv_dialect' in request.session:
            path_and_file = request.session['save_path']
            csv_dialect = request.session['csv_dialect']
            encoding = request.encoding
        else:
            print("request param for file_to_array function is invalid")
    else:
        print("request and model parameters both None in file_to_array function")
        return False

    #TODO is user exists
    # mappings = Mapping.objects.filter(user=request.user.id)
    # file_name = mappings.

    csv_array = []

    if not os.path.exists(path_and_file):
        print("File", path_and_file, "does not exist!")
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
                if start_row < 0:
                    # take all
                    start_row = 1
                    num_rows = row_count
            if num_rows == -1:
                start_row = 1
                num_rows = row_count

            r = range(start_row, start_row + num_rows)
            print(r)
            for i, row in enumerate(csv_reader):
                if i in r:
                    csv_array.append(row)

            # removal of blanks, especially special blanks \xA0 etc.
            for i, row in enumerate(csv_array):
                for j, field in enumerate(row):
                    csv_array[i][j] = field.strip()

    #for x in csv_array:
    #    print(" > ", x)

    secs = datetime.datetime.now() -time1
    print(num_rows," / ", row_count, " rows in " + str(secs))

    return {'rows': csv_array, 'start_row': start_row_original, 'num_rows': num_rows}
