# avtohim_site/urls.py (фрагмент)
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from avtohim_site import views


handler404 = "core.views.error_404"
handler500 = "core.views.error_500"


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", core_views.home, name="home"),
    path("services/", core_views.service_list, name="service_list"),
    path("services/<slug:slug>/", core_views.service_detail, name="service_detail"),
    path("products/", core_views.product_list, name="product_list"),
    path("products/<slug:slug>/", core_views.product_detail, name="product_detail"),
    path("lead/", core_views.lead_create, name="lead_create"),
    path("contacts/", core_views.contacts, name="contacts"),
    path("faq/", core_views.faq_page, name="faq_page"),
    path("reviews/new/", core_views.review_create, name="review_create"),
    
    prefix_default_language=False,
    
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
