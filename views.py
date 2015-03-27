from django.http import HttpResponseRedirect
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from .forms import *
from django.core.urlresolvers import reverse
import csv
from io import TextIOWrapper


def index(request):
    print("CSV")
    if request.method == 'POST':
        # handle the uploaded file here
        raise





def csv_upload(request):
    if request.method == 'POST':
        #print('  --  csv upload: POST  --  ')        
        if not request.FILES:
            form = UploadFileForm(request.POST)
            if request.POST and form.is_valid():
                print('POST')
                print(request.POST)
                rows = eval(form.cleaned_data['hidden_csvContent_field'])
                separator_proposal = '|'
                uploadFileName = form.cleaned_data['hidden_filename_field']
            else:
                rows = None
                separator_proposal = None
                uploadFileName = 'no file selected'

        else:
            form = UploadFileForm(request.POST, request.FILES)
        
            uploadFileName = request.FILES['upload_file'].name

            if form.is_valid():
                csvRows = []
                csvLines = []
                rows = []

                # https://docs.python.org/2/library/csv.html#
                with TextIOWrapper(request.FILES['upload_file'].file, encoding=request.encoding) as csvfile:
                    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
                    for row in spamreader:
                        print(', '.join(row))
                        csvRows.append(row)
                '''
                # separator_proposal DETECTION
                separator_proposal = None
                if len(csvRows) > 0:
                    #check which separator_proposal occurs the most
                    separators = {',': 0, ';': 0, '\t': 0, ':': 0}
                    for key in separators:
                        separators[key] = csvRows[0].count(key)
                    separator_proposal = max(separators, key=separators.get)
                    csvLines = csvRows[0].split("\n", 10)
    
                if len(csvLines) > 0:
                    # pop last item from array as it contains the 'rest' that wasn't split by the split function
                    csvLines.pop(len(csvLines)-1)
                    for line in csvLines:
                        rows.append(line.split(separator_proposal))
    
                if separator_proposal=="\t":
                    separator_proposal="tab"
                '''
                separator_proposal = "none" #TODO
                # which button was pressed?
                # http://stackoverflow.com/questions/866272/how-can-i-build-multiple-submit-buttons-django-form
        if 'button_upload' in request.POST:
            return render_to_response('transformation/csv_upload.html', {'form': form, 'csvContent': csvRows, 'separator_proposal': separator_proposal, 'filename': uploadFileName}, context_instance=RequestContext(request))
        elif 'button_next' in request.POST:
            return render_to_response('transformation/csv_column_choice.html', {'form': form, 'csvContent': csvRows, 'separator_proposal': separator_proposal, 'filename': uploadFileName}, context_instance=RequestContext(request))
                # TODO send datamodel id here instead of csv content

    else:
        print('Form not valid!')
        form = UploadFileForm()
        return render_to_response('transformation/csv_upload.html', {'form': form}, context_instance=RequestContext(request))





def csv_column_choice(request):
    if request.method == 'POST':
        form = CsvColumnChoiceForm(request.POST, request.FILES)
        if form.is_valid():
            print('  --  csv column choice: POST  --  ')
            return render_to_response('transformation/csv_column_choice.html', {'form': form}, context_instance=RequestContext(request))
        else:
            print('form not valid')
            print(form.errors)
    else:
        print('Form not valid!')
        form = DataChoiceForm()
    return render_to_response('transformation/csv_column_choice.html', {'form': form}, context_instance=RequestContext(request))





def data_choice(request):
    if request.method == 'POST':
        form = DataChoiceForm(request.POST, request.FILES)
        if form.is_valid():
            print('  --  data choice: POST  --  ')
            return render_to_response('transformation/data_choice.html', {'form': form}, context_instance=RequestContext(request))
        else:
            print('form not valid')
            print(form.errors)
    else:
        print('Form not valid!')
        form = DataChoiceForm()
    return render_to_response('transformation/data_choice.html', {'form': form}, context_instance=RequestContext(request))
