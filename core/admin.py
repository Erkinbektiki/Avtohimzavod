# core/admin.py
from django.contrib import admin
from . import translation
from .models import SiteSettings
from django.utils.text import slugify
from unidecode import unidecode
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from .models import Service, Case, FAQ, Review, Branch

def autoslug(value):
    """
    Транслитерирует и слагает.
    """
    return slugify(unidecode(value))[:200]

class FAQInline(TranslationTabularInline):
    model = FAQ
    extra = 0
    fields = ("question", "answer", "order", "is_published")

class CaseInline(TranslationTabularInline):
    model = Case
    extra = 0
    fields = ("title", "slug", "before_image", "after_image", "metric_label", "metric_before", "metric_after", "video_url", "is_published")

@admin.register(Service)
class ServiceAdmin(TranslationAdmin):
    list_display = ("title", "category", "price_from", "is_published", "order")
    list_filter = ("category", "is_published")
    search_fields = ("title", "short_desc")
    inlines = [FAQInline]
    fieldsets = (
        (None, {"fields": ("category", "title", "slug", "short_desc", "body", "price_from", "cover", "order", "is_published")}),
        ("SEO", {"fields": ("meta_title", "meta_description")}),
    )

    def save_model(self, request, obj, form, change):
        # если slug'и пустые — автогенерируем из title для всех языков
        for code in ("", "_ky", "_en"):
            t = getattr(obj, f"title{code}", None)
            s = getattr(obj, f"slug{code}", None)
            if t and not s:
                setattr(obj, f"slug{code}", autoslug(t))
        super().save_model(request, obj, form, change)

@admin.register(Case)
class CaseAdmin(TranslationAdmin):
    list_display = ("title", "service", "is_published", "created_at")
    list_filter = ("is_published", "service")
    search_fields = ("title",)
    fieldsets = (
        (None, {"fields": ("service", "title", "slug", "before_image", "after_image")}),
        ("Метрики и видео", {"fields": ("metric_label", "metric_before", "metric_after", "video_url")}),
        ("Публикация", {"fields": ("is_published",)}),
    )

    def save_model(self, request, obj, form, change):
        for code in ("", "_ky", "_en"):
            t = getattr(obj, f"title{code}", None)
            s = getattr(obj, f"slug{code}", None)
            if t and not s:
                setattr(obj, f"slug{code}", autoslug(t))
        super().save_model(request, obj, form, change)

@admin.register(FAQ)
class FAQAdmin(TranslationAdmin):
    list_display = ("question", "service", "order", "is_published")
    list_filter = ("is_published", "service")
    search_fields = ("question",)

try:
    from modeltranslation.admin import TranslationAdmin as BaseAdmin
except Exception:
    from django.contrib.admin import ModelAdmin as BaseAdmin

@admin.register(Review)
class ReviewAdmin(BaseAdmin):
    list_display = ("author", "rating", "source", "is_published", "created_at")
    list_filter = ("is_published", "rating", "source")
    search_fields = ("author", "text")
    ordering = ("-created_at",)

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # разрешаем создать только одну запись
        return not SiteSettings.objects.exists()
    
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "address_locality", "is_active", "sort")
    list_editable = ("is_active", "sort")
    search_fields = ("name", "street_address", "address_locality")
    prepopulated_fields = {"slug": ("name",)}