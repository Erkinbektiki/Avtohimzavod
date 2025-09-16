# core/context_processors.py

from django.db.models import Avg, Count
from .models import SiteSettings, Review, Branch  # добавили Review

def site_settings(request):
    SITESET = SiteSettings.get_solo()
    agg = Review.objects.filter(is_published=True).aggregate(avg=Avg("rating"), cnt=Count("id"))
    rating = {
        "value": round(agg["avg"] or 0, 1),
        "count": agg["cnt"] or 0,
    }
    return {"SITESET": SITESET, "SITE_RATING": rating}

def branches(request):
    return {"BRANCHES": Branch.objects.filter(is_active=True)}
