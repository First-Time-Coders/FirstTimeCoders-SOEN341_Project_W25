# from django.http import HttpResponse
from django.shortcuts import render
def Homepage(request):
    # return HttpResponse('Hello, World!')
    return render(request, 'api/Home.html')

def About(request):
    # return HttpResponse('About Page')
    return render(request, 'api/About.html')



