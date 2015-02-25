from django.shortcuts import render


def csv_view(request):
    if request.method == 'POST':
        # handle the uploaded file here
        raise


def index(request):
    return render(request, 'transformation/index.html', {})