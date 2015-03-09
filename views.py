from django.http import HttpResponseRedirect
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from .forms import UploadFileForm


def csv_view(request):
    print("CSV")
    if request.method == 'POST':
        # handle the uploaded file here
        raise


def index(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            for chunk in request.FILES['file'].chunks():
                print(chunk)
            return HttpResponseRedirect('')
    else:
        form = UploadFileForm()
    return render_to_response('transformation/index.html', {'form': form}, context_instance=RequestContext(request))