# core/models.py
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from model_utils.models import TimeStampedModel
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from sorl.thumbnail import ImageField
from django import forms

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Service(TimeStampedModel):
    ENGINE = "engine"
    DIAG = "diagnostics"
    FLUIDS = "fluids"
    DETAILING = "detailing"

    CATEGORY_CHOICES = [
        (ENGINE, "Раскоксовка/двигатель"),
        (DIAG, "Диагностика"),
        (FLUIDS, "Автохимия/жидкости"),
        (DETAILING, "Детейлинг"),
    ]

    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default=ENGINE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, help_text="URL-часть (RU)")
    short_desc = models.TextField(blank=True)
    body = models.TextField(blank=True)
    price_from = models.PositiveIntegerField(null=True, blank=True, help_text="Цена от, сом")
    cover = models.ImageField(upload_to="services/covers/", null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    # SEO
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=350, blank=True)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """
        Возвращает URL с локализованным slug (если заполнены slug_ky / slug_en).
        """
        from django.utils.translation import get_language
        lang = get_language() or settings.LANGUAGE_CODE
        localized = getattr(self, f"slug_{lang}", None)
        slug = localized or self.slug
        return reverse("service_detail", kwargs={"slug": slug})

class Case(TimeStampedModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="cases")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    before_image = models.ImageField(upload_to="cases/before/")
    after_image = models.ImageField(upload_to="cases/after/")
    metric_label = models.CharField(max_length=120, blank=True, help_text="Напр., 'Компрессия'")
    metric_before = models.CharField(max_length=50, blank=True, help_text="Напр., '8 бар'")
    metric_after = models.CharField(max_length=50, blank=True, help_text="Напр., '13 бар'")
    video_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

class FAQ(TimeStampedModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="faqs", null=True, blank=True)
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.question

class ReviewQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

class Review(TimeStampedModel):
    class Source(models.TextChoices):
        GOOGLE = "google", "Google"
        GIS2   = "2gis", "2ГИС"
        IG     = "instagram", "Instagram"
        MANUAL = "manual", _("Ручной ввод")

    author = models.CharField(_("Имя"), max_length=120)
    rating = models.PositiveSmallIntegerField(
        _("Оценка"),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField(_("Отзыв"))
    source = models.CharField(_("Источник"), max_length=20,
                              choices=Source.choices, default=Source.MANUAL)
    source_url = models.URLField(_("Ссылка на источник"), blank=True)
    is_published = models.BooleanField(_("Показывать"), default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Отзыв")
        verbose_name_plural = _("Отзывы")

    def __str__(self):
        return f"{self.author} ({self.rating}/5)"

class Lead(TimeStampedModel):
    class Status(models.TextChoices):
        NEW = "new", _("Новая")
        INWORK = "inwork", _("В работе")
        DONE = "done", _("Завершена")

    name = models.CharField(_("Имя"), max_length=120)
    phone = models.CharField(_("Телефон"), max_length=32)
    message = models.TextField(_("Комментарий"), blank=True)
    service = models.ForeignKey(
        Service, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Услуга")
    )
    lang = models.CharField(_("Язык"), max_length=8, default="ru")
    status = models.CharField(_("Статус"), max_length=16, choices=Status.choices, default=Status.NEW)

    # простые UTM для аналитики
    utm_source = models.CharField(max_length=64, blank=True)
    utm_medium = models.CharField(max_length=64, blank=True)
    utm_campaign = models.CharField(max_length=64, blank=True)

    consent = models.BooleanField(_("Согласие с политикой"), default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Заявка")
        verbose_name_plural = _("Заявки")

    def __str__(self):
        return f"{self.name} / {self.phone}"

class SiteSettings(TimeStampedModel):
    # Бренд и описание
    brand = models.CharField(_("Бренд"), max_length=120, default="Avto_Him_Zavod")
    description = models.CharField(_("Короткое описание"), max_length=255, blank=True)

    # Контакты (NAP)
    phone_display = models.CharField(_("Телефон (для показа)"), max_length=32, default="+996 XXX XX-XX-XX")
    phone_e164 = models.CharField(_("Телефон в E.164"), max_length=32, default="+996")
    whatsapp_link = models.URLField(_("Ссылка WhatsApp"), blank=True)
    telegram_link = models.URLField(_("Ссылка Telegram"), blank=True)
    email = models.EmailField(_("Email"), blank=True)

    # Адрес
    street_address = models.CharField(_("Адрес"), max_length=255, default="ул. Алматинская, 8")
    address_locality = models.CharField(_("Город"), max_length=120, default="Бишкек")
    address_region = models.CharField(_("Регион"), max_length=120, default="Чуйская область")
    postal_code = models.CharField(_("Индекс"), max_length=20, blank=True)
    address_country = models.CharField(_("Страна (ISO2 или название)"), max_length=64, default="KG")

    # Координаты
    geo_lat = models.DecimalField(_("Широта"), max_digits=9, decimal_places=6, null=True, blank=True)
    geo_lng = models.DecimalField(_("Долгота"), max_digits=9, decimal_places=6, null=True, blank=True)

    # Часы работы
    hours_mon = models.CharField(_("Пн"), max_length=50, default="09:00-18:00")
    hours_tue = models.CharField(_("Вт"), max_length=50, default="09:00-18:00")
    hours_wed = models.CharField(_("Ср"), max_length=50, default="09:00-18:00")
    hours_thu = models.CharField(_("Чт"), max_length=50, default="09:00-18:00")
    hours_fri = models.CharField(_("Пт"), max_length=50, default="09:00-18:00")
    hours_sat = models.CharField(_("Сб"), max_length=50, default="10:00-17:00")
    hours_sun = models.CharField(_("Вс"), max_length=50, default="closed")

    # Новое поле: видео на главной
    hero_youtube_id = models.CharField(
        _("YouTube ID главного видео"),
        max_length=50,
        blank=True,
        help_text=_("ID видео с YouTube, например: dQw4w9WgXcQ из https://youtu.be/dQw4w9WgXcQ")
    )

    class Meta:
        verbose_name = _("Настройки сайта")
        verbose_name_plural = _("Настройки сайта")

    def __str__(self):
        return "Настройки сайта"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj
class Brand(models.Model):
    title = models.CharField(_("Бренд"), max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    logo = ImageField(_("Логотип"), upload_to="brands/", blank=True)

    class Meta:
        verbose_name = _("Бренд")
        verbose_name_plural = _("Бренды")
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class ProductCategory(models.Model):
    title = models.CharField(_("Категория"), max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    class Meta:
        verbose_name = _("Категория товара")
        verbose_name_plural = _("Категории товаров")
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class Product(models.Model):
    title = models.CharField(_("Название"), max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Бренд"))
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Категория"))
    cover = ImageField(_("Обложка"), upload_to="products/", blank=True)
    short_desc = models.TextField(_("Краткое описание"), blank=True)
    full_desc = models.TextField(_("Полное описание"), blank=True)

    # необязательные «торговые» поля (можем не показывать цену — тогда будет «Уточнить цену»)
    price = models.PositiveIntegerField(_("Цена, сом"), null=True, blank=True)
    unit = models.CharField(_("Единица"), max_length=40, blank=True, help_text=_("Напр.: 1 л, 4 л, канистра 20 л"))
    is_published = models.BooleanField(_("Показывать на сайте"), default=True)
    in_stock = models.BooleanField(_("В наличии"), default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Товар")
        verbose_name_plural = _("Товары")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            i = 2
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.slug])

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = ImageField(_("Фото"), upload_to="products/gallery/")
    alt = models.CharField(_("ALT"), max_length=200, blank=True)
    sort = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = _("Фото товара")
        verbose_name_plural = _("Фотографии товара")

    def __str__(self):
        return f"{self.product} #{self.id}"

class Branch(models.Model):
    name = models.CharField("Название филиала", max_length=120)
    slug = models.SlugField("Слаг", unique=True)
    phone_e164 = models.CharField("Телефон в E.164", max_length=20, blank=True)
    whatsapp_link = models.URLField("WhatsApp ссылка", blank=True)

    street_address = models.CharField("Улица, дом", max_length=180)
    address_locality = models.CharField("Город/район", max_length=120, default="Бишкек")
    address_region = models.CharField("Регион", max_length=120, default="Чуйская область")
    address_country = models.CharField("Страна", max_length=2, default="KG")

    geo_lat = models.DecimalField("Широта", max_digits=9, decimal_places=6)
    geo_lng = models.DecimalField("Долгота", max_digits=9, decimal_places=6)

    hours_mon = models.CharField("Пн–Пт", max_length=60, blank=True, default="09:00–18:00")
    hours_sat = models.CharField("Сб", max_length=60, blank=True, default="10:00–16:00")
    hours_sun = models.CharField("Вс", max_length=60, blank=True, default="выходной")

    is_active = models.BooleanField("Показывать на сайте", default=True)
    sort = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ("sort", "name")
        verbose_name = "Филиал"
        verbose_name_plural = "Филиалы"

    def __str__(self):
        return self.name

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        # На сайте обычно не даём посетителю управлять публикацией,
        # поэтому is_published исключаем — им будете управлять в админке.
        fields = ["author", "rating", "text", "source", "source_url"]

        labels = {
            "author": "Имя",
            "rating": "Оценка",
            "text": "Отзыв",
            "source": "Источник",
            "source_url": "Ссылка на источник",
        }

        widgets = {
            "author": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ваше имя"}),
            "rating": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Текст отзыва"}),
            "source": forms.Select(attrs={"class": "form-control"}),
            "source_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }

    def clean_rating(self):
        r = self.cleaned_data.get("rating")
        if r is None:
            return r
        if not (1 <= r <= 5):
            raise forms.ValidationError("Оценка должна быть от 1 до 5.")
        return r