# core/translation.py
from modeltranslation.translator import translator, TranslationOptions
from .models import Service, Case, FAQ, Review

class ServiceTranslationOptions(TranslationOptions):
    fields = ("title", "slug", "short_desc", "body", "meta_title", "meta_description")

class CaseTranslationOptions(TranslationOptions):
    fields = ("title", "slug")

class FAQTranslationOptions(TranslationOptions):
    fields = ("question", "answer")

class ReviewTranslationOptions(TranslationOptions):
    fields = ("text",)

translator.register(Service, ServiceTranslationOptions)
translator.register(Case, CaseTranslationOptions)
translator.register(FAQ, FAQTranslationOptions)
translator.register(Review, ReviewTranslationOptions)
