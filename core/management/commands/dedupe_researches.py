# =========================================
# file: core/management/commands/dedupe_researches.py
# =========================================
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Research, ResearchSupervision


class Command(BaseCommand):
    help = "Merge duplicate Research rows (same researcher_name + title + degree + researcher_type)."

    @transaction.atomic
    def handle(self, *args, **options):
        groups = defaultdict(list)
        for r in Research.objects.all().order_by("id"):
            key = (r.researcher_name.strip(), (r.title or "").strip(), r.degree, r.researcher_type)
            groups[key].append(r)

        merged = 0
        deleted = 0
        moved_links = 0

        for _, items in groups.items():
            if len(items) <= 1:
                continue

            keep = items[0]
            # prefer record with researcher dept (if any)
            for cand in items:
                if cand.department_id is not None:
                    keep = cand
                    break

            for dup in [x for x in items if x.id != keep.id]:
                for link in ResearchSupervision.objects.filter(research=dup).select_related("supervisor"):
                    obj, created = ResearchSupervision.objects.get_or_create(
                        research=keep,
                        supervisor=link.supervisor,
                        defaults={"role": link.role},
                    )
                    if created:
                        moved_links += 1

                dup.delete()
                deleted += 1

            merged += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Groups merged: {merged} | Duplicates deleted: {deleted} | Links moved: {moved_links}"
        ))