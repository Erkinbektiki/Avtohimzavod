# core/views.py
import json
import urllib.request

import os, requests
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import get_language, gettext as _
from django.views.decorators.http import require_POST, require_http_methods

from .forms import LeadForm, ReviewForm
from .models import Service, Case, FAQ, Review, Lead, Product, ProductCategory, Brand, FAQ
from .tele_notify import notify_lead



def home(request):
    services = Service.objects.filter(is_published=True).order_by("order")
    form = LeadForm(initial={
        "lang": get_language() or "ru",
        "utm_source": request.GET.get("utm_source",""),
        "utm_medium": request.GET.get("utm_medium",""),
        "utm_campaign": request.GET.get("utm_campaign",""),
    })
    reviews = Review.objects.filter(is_published=True).order_by("-created_at")[:6]
    return render(request, "home.html", {
        "services": services,
        "form_lead": form,
        "reviews": reviews,
    })

def _localized_slug_filter(field_base: str, slug_value: str):
    """
    Возвращает dict для фильтрации по локализованному slug.
    """
    lang = get_language() or settings.LANGUAGE_CODE
    field = f"{field_base}_{lang}" if lang != settings.LANGUAGE_CODE else field_base
    return {field: slug_value}

def service_list(request):
    services = Service.objects.filter(is_published=True).order_by("order")
    return render(request, "services/list.html", {"services": services})

def service_detail(request, slug):
    svc = get_object_or_404(Service, is_published=True, **_localized_slug_filter("slug", slug))
    cases = svc.cases.filter(is_published=True)[:9]
    faqs = svc.faqs.filter(is_published=True).order_by("order", "id")
    reviews = Review.objects.filter(is_published=True)[:6]

    form = LeadForm(initial={
        "service": svc.id,
        "lang": get_language() or "ru",
        "utm_source": request.GET.get("utm_source",""),
        "utm_medium": request.GET.get("utm_medium",""),
        "utm_campaign": request.GET.get("utm_campaign",""),
    })

    return render(request, "services/detail.html", {
        "service": svc, "cases": cases, "faqs": faqs, "reviews": reviews,
        "LeadForm": LeadForm, "form_lead": form
    })

def _post_to_n8n(payload: dict):
    """
    Отправка данных в n8n, если настроен WEBHOOK.
    Безопасно молчит при ошибке.
    """
    url = getattr(settings, "N8N_WEBHOOK_URL", "")
    if not url:
        return
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
    except Exception:
        # логировать по желанию
        pass

@require_POST
def lead_create(request):
    form = LeadForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    lead = form.save()  # у тебя уже сохранение в БД

    # Вебхук в n8n (не блокируем пользователя при сбое)
    url = getattr(settings, "N8N_WEBHOOK_URL", "")
    if url:
        try:
            payload = {
                "id": lead.id,
                "name": lead.name,
                "phone_e164": lead.phone_e164,
                "service": getattr(lead.service, "title", ""),
                "comment": lead.comment,
                "utm_source": lead.utm_source,
                "utm_medium": lead.utm_medium,
                "utm_campaign": lead.utm_campaign,
                "lang": request.LANGUAGE_CODE,
            }
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass  # просто логируй при желании

    return JsonResponse({"ok": True})
    
def contacts(request):
    return render(request, "contacts.html")

def faq_page(request):
    faqs = FAQ.objects.filter(is_published=True, service__isnull=True).order_by("order","id")
    return render(request, "faq.html", {"faqs": faqs})

def error_404(request, exception):
    return render(request, "errors/404.html", status=404)

def error_500(request):
    return render(request, "errors/500.html", status=500)

def product_list(request):
    qs = Product.objects.filter(is_published=True)
    cat_slug = request.GET.get("cat")
    brand_slug = request.GET.get("brand")
    if cat_slug:
        qs = qs.filter(category__slug=cat_slug)
    if brand_slug:
        qs = qs.filter(brand__slug=brand_slug)

    cats = ProductCategory.objects.all()
    brands = Brand.objects.all()
    return render(request, "products/list.html", {
        "products": qs,
        "cats": cats,
        "brands": brands,
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_published=True)
    # ссылка в WhatsApp с префиллом
    wa = getattr(request, "SITESET", None) or {}
    whatsapp_link = getattr(wa, "whatsapp_link", None)
    return render(request, "products/detail.html", {
        "p": product,
        "whatsapp_link": whatsapp_link,
    })

@require_POST
def lead_create(request):
    form = LeadForm(request.POST)
    if form.is_valid():
        lead = form.save()

        # Сформируем данные для телеги
        payload = {
            "name": getattr(lead, "name", "") or request.POST.get("name"),
            "phone_e164": getattr(lead, "phone_e164", "") or request.POST.get("phone"),
            "service": getattr(lead, "service_name", "") or request.POST.get("service"),
            "comment": getattr(lead, "comment", "") or request.POST.get("comment"),
            "utm_source": request.POST.get("utm_source"),
            "utm_medium": request.POST.get("utm_medium"),
            "utm_campaign": request.POST.get("utm_campaign"),
        }
        notify_lead(payload)  # ← отправка в Telegram

        messages.success(request, "Спасибо! Мы свяжемся с вами в ближайшее время.")
        return redirect("home")
    else:
        messages.error(request, "Проверьте корректность данных в форме.")
        # если у вас на главной эта форма, верните тот же шаблон с контекстом
        return redirect("home")
    
def faq_page(request):
    faqs = FAQ.objects.filter(is_published=True).order_by('order') if hasattr(FAQ, 'objects') else []
    return render(request, "faq/page.html", {"faqs": faqs})

@require_http_methods(["GET", "POST"])
def review_create(request):
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # по желанию: obj.is_published = False  # премодерация
            obj.save()
            messages.success(request, "Спасибо! Ваш отзыв отправлен на модерацию.")
            return redirect("home")  # или на страницу «спасибо»
    else:
        form = ReviewForm()

    return render(request, "reviews/create.html", {"form": form})

def notify_tg(text):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if token and chat_id:
        try:
            requests.get(
                f"https://api.telegram.org/bot{token}/sendMessage",
                params={"chat_id": chat_id, "text": text},
                timeout=5,
            )
        except Exception:
            pass

# в review_create после save():
# notify_tg(f"📝 Новый отзыв: {obj.name or '—'}\nРейтинг: {obj.rating}/5\n{obj.text[:400]}")