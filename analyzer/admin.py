from django.contrib import admin
from .models import LibraryPaper, AnalysisSession, ExamPaper, AnalysisResult


@admin.register(LibraryPaper)
class LibraryPaperAdmin(admin.ModelAdmin):
    list_display  = ('title', 'student_class', 'subject', 'year', 'set_name', 'total_marks', 'uploaded_at')
    list_filter   = ('student_class', 'subject', 'year')
    search_fields = ('title', 'year', 'subject')
    ordering      = ('-year', 'student_class', 'subject')
    fieldsets = (
        ('Paper Identity', {
            'fields': ('title', 'title_hindi', 'student_class', 'subject', 'year', 'set_name', 'total_marks')
        }),
        ('File & Visibility', {
            'fields': ('pdf_file',)
        }),
    )


@admin.register(AnalysisSession)
class AnalysisSessionAdmin(admin.ModelAdmin):
    list_display    = ('id', 'user', 'student_class', 'subject', 'status', 'created_at')
    list_filter     = ('status', 'student_class', 'subject')
    search_fields   = ('user__username', 'subject')
    readonly_fields = ('id', 'created_at')
    ordering        = ('-created_at',)


@admin.register(ExamPaper)
class ExamPaperAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'library_paper')
    list_filter  = ('library_paper__subject',)


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display    = ('id', 'session', 'created_at')
    readonly_fields = ('created_at',)
