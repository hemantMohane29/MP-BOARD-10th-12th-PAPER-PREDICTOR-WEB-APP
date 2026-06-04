import uuid
from django.db import models
from django.contrib.auth.models import User


class LibraryPaper(models.Model):
    """Pre-loaded question papers managed by admin. Students select from these."""

    title         = models.CharField(max_length=200, help_text="e.g., MP Board Class 10th Science 2024")
    title_hindi   = models.CharField(max_length=200, blank=True, help_text="e.g., कक्षा 10वीं विज्ञान 2024")
    student_class = models.CharField(max_length=10)
    subject       = models.CharField(max_length=100)
    year          = models.CharField(max_length=10, help_text="e.g., 2024")
    set_name      = models.CharField(max_length=20, blank=True, help_text="e.g., Set A")
    total_marks   = models.IntegerField(default=80)
    pdf_file      = models.FileField(upload_to='library/papers/', help_text="Upload PDF or Image (.jpg, .png)")
    uploaded_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', 'subject']




class AnalysisSession(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    student_class = models.CharField(max_length=50)
    subject       = models.CharField(max_length=100)
    status        = models.CharField(max_length=50, default='pending')
    error_message = models.TextField(blank=True, null=True, help_text="Stores the error if the pipeline fails")
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']




class ExamPaper(models.Model):
    """One paper slot inside an AnalysisSession. Links to a LibraryPaper."""
    session       = models.ForeignKey(AnalysisSession, related_name='papers', on_delete=models.CASCADE)
    library_paper = models.ForeignKey(LibraryPaper, on_delete=models.CASCADE,
                                      help_text="Pre-loaded library paper used for this analysis")
    ocr_raw_text  = models.TextField(blank=True, null=True, help_text="Raw OCR output from Sarvam API")
    extracted_questions_json = models.JSONField(blank=True, null=True, help_text="JSON list of questions extracted from this paper")

    def get_file_path(self):
        """Returns the filesystem path to the file (PDF or Image) from the linked library paper."""
        return self.library_paper.pdf_file.path




class AnalysisResult(models.Model):
    session                  = models.OneToOneField(AnalysisSession, related_name='result', on_delete=models.CASCADE)
    stage_2_deduplicated_json = models.JSONField(blank=True, null=True)
    stage_3_dl_insights_json  = models.JSONField(blank=True, null=True)
    created_at               = models.DateTimeField(auto_now_add=True)
