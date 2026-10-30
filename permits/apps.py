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

        # Resilient In-Process Scheduler for Automatic Daily Backup & Cloud Sync
        import os
        if os.environ.get('RUN_MAIN') == 'true' or ('runserver' not in sys.argv and 'test' not in sys.argv):
            try:
                self._start_background_scheduler()
            except Exception:
                pass

    def _start_background_scheduler(self):
        import threading
        import time

        def scheduler_loop():
            # Grace period after server startup
            time.sleep(8)
            while True:
                try:
                    from django.db import connection
                    connection.close()
                    from django.utils import timezone
                    from permits.services import execute_automated_backup
                    from permits.storage import sync_all_local_files_to_supabase
                    from permits.models import AuditLog
                    from django.db.models import Q

                    now = timezone.now()
                    local_now = timezone.localtime(now)
                    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

                    # Check if a backup was completed today
                    ran_today = AuditLog.objects.filter(
                        Q(action__icontains='Automated System Backup') | Q(action__icontains='Exported full database backup')
                    ).filter(performed_at__gte=today_start).exists()

                    if not ran_today:
                        execute_automated_backup(skip_if_already_backed_up_today=False)
                        sync_all_local_files_to_supabase()
                except Exception:
                    pass
                finally:
                    try:
                        from django.db import connection
                        connection.close()
                    except Exception:
                        pass

                # Check every 15 minutes for midnight transition or missed backup
                time.sleep(900)

        t = threading.Thread(target=scheduler_loop, daemon=True, name="eTala-AutoBackupScheduler")
        t.start()

