from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Lead, Review

class LeadForm(forms.ModelForm):
    # honeypot (от ботов)
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Lead
        fields = ["name", "phone", "message", "service", "lang", "utm_source", "utm_medium", "utm_campaign"]
        widgets = {
            "service": forms.HiddenInput,
            "lang": forms.HiddenInput,
            "utm_source": forms.HiddenInput,
            "utm_medium": forms.HiddenInput,
            "utm_campaign": forms.HiddenInput,
            "message": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "name": _("Имя"),
            "phone": _("Телефон"),
            "message": _("Комментарий"),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):  # бот заполнил скрытое поле
            raise forms.ValidationError(_("Проверьте форму"))
        return cleaned

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        # ровно те поля, которые есть в модели
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