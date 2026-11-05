import django
from django.conf import settings

settings.configure(
    OPENAI_SECRET_KEY="sk-test",
    TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates"}],
)
django.setup()
