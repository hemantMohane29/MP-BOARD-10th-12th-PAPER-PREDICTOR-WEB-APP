"""
Management command: seed_papers
Scans media/library/papers/ and creates LibraryPaper records for any
PDF/image files that aren't already in the database.

Usage:  python manage.py seed_papers
Called automatically from start.sh on every startup.
"""
import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from analyzer.models import LibraryPaper


# Map filename prefixes → (subject, student_class)
SUBJECT_MAP = {
    'Biology':     ('Biology',          '12th'),
    'Chemistry':   ('Chemistry',        '12th'),
    'Physics':     ('Physics',          '12th'),
    'Maths':       ('Maths',            None),   # class determined from filename
    'Hindi':       ('Hindi',            None),
    'English':     ('English',          None),
    'Science':     ('Science',          '10th'),
    'So-Science':  ('Social Science',   '10th'),
}


def parse_filename(filename):
    """
    Parse Subject_Class_Year[_suffix].pdf  →  (subject, student_class, year, title)
    e.g. Science_10th_2023.pdf  →  ('Science', '10th', '2023', 'Science 10th 2023')
         Physics_12th_2020_0s9UUQD.pdf  →  ('Physics', '12th', '2020', ...)
    """
    name = os.path.splitext(filename)[0]        # strip extension
    name = re.sub(r'_[A-Za-z0-9]{5,}$', '', name)   # strip Django upload suffix

    parts = name.split('_')
    # Find year (4-digit number)
    year = None
    year_idx = None
    for i, p in enumerate(parts):
        if re.fullmatch(r'20\d{2}', p):
            year = p
            year_idx = i
            break

    if year is None:
        return None  # can't parse, skip

    # Class is the part before year that looks like 10th/12th
    student_class = None
    subject_parts = []
    for i, p in enumerate(parts):
        if i == year_idx:
            break
        if re.fullmatch(r'\d+(th|st|nd|rd)', p, re.IGNORECASE):
            student_class = p.lower().replace('th','th')
        else:
            subject_parts.append(p)

    subject_raw = '_'.join(subject_parts)  # e.g. "So-Science" or "Science"

    # Look up canonical subject name
    subject = None
    for key, (subj, cls) in SUBJECT_MAP.items():
        if subject_raw == key:
            subject = subj
            if student_class is None and cls is not None:
                student_class = cls
            break

    if subject is None:
        subject = subject_raw.replace('-', ' ')  # fallback

    if student_class is None:
        student_class = '10th'  # fallback

    title = f'{subject} {student_class} {year}'
    return subject, student_class, year, title


class Command(BaseCommand):
    help = 'Seed LibraryPaper records from media/library/papers/'

    def handle(self, *args, **options):
        papers_dir = os.path.join(settings.MEDIA_ROOT, 'library', 'papers')

        if not os.path.exists(papers_dir):
            self.stdout.write(self.style.WARNING(f'Papers directory not found: {papers_dir}'))
            return

        files = [
            f for f in os.listdir(papers_dir)
            if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png'))
            and not f.startswith('.')
        ]

        created = 0
        skipped = 0

        for filename in sorted(files):
            # Skip duplicate-suffix files (e.g. Physics_12th_2020_0s9UUQD.pdf)
            # Keep only the clean version when both exist
            name_no_ext = os.path.splitext(filename)[0]
            if re.search(r'_[A-Za-z0-9]{5,}$', name_no_ext):
                skipped += 1
                continue

            parsed = parse_filename(filename)
            if parsed is None:
                self.stdout.write(self.style.WARNING(f'  Skipping unparseable: {filename}'))
                skipped += 1
                continue

            subject, student_class, year, title = parsed
            relative_path = f'library/papers/{filename}'

            # Skip if already exists
            if LibraryPaper.objects.filter(pdf_file=relative_path).exists():
                skipped += 1
                continue

            LibraryPaper.objects.create(
                title=title,
                title_hindi='',
                student_class=student_class,
                subject=subject,
                year=year,
                set_name='',
                total_marks=80,
                pdf_file=relative_path,
            )
            created += 1
            self.stdout.write(f'  + {title}')

        self.stdout.write(self.style.SUCCESS(
            f'Seed complete: {created} papers created, {skipped} skipped.'
        ))
