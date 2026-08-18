from django.apps import AppConfig
import sys


class PermitsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'permits'
    verbose_name = 'Building Permit System'

    def ready(self):
        try:
            from django.db.models.signals import post_migrate
            def clean_legacy_requirement_names(sender, **kwargs):
                from permits.models import RequirementItem
                import re
                try:
                    for item in RequirementItem.objects.filter(name__contains='('):
                        clean_name = re.sub(r'\s*\([a-z]\.\d+\)', '', item.name).strip()
                        if clean_name != item.name:
                            item.name = clean_name
                            item.save(update_fields=['name'])
                except Exception:
                    pass

            post_migrate.connect(clean_legacy_requirement_names, sender=self)
        except Exception:
            pass

