from django.contrib import admin
from .models import CallSession


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ('caller', 'receiver', 'call_type', 'status', 'created_at', 'get_duration_display')
    list_filter = ('call_type', 'status', 'created_at')
    search_fields = ('caller__username', 'receiver__username')
    readonly_fields = ('created_at', 'started_at', 'ended_at')
    
    def get_duration_display(self, obj):
        return obj.format_duration()
    get_duration_display.short_description = 'Duration'
