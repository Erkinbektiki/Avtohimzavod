from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return HttpResponse("Главная страница")

def review_create(request):
    return HttpResponse("Создание отзыва")