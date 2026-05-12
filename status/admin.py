from django.contrib import admin
from .models import Status, StatusView, StatusHidden


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at', 'is_expired')
    list_filter = ('created_at', 'expires_at')
    search_fields = ('user__username', 'content')
    readonly_fields = ('created_at',)
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True


@admin.register(StatusView)
class StatusViewAdmin(admin.ModelAdmin):
    list_display = ('status', 'viewer', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('viewer__username', 'status__user__username')
    readonly_fields = ('viewed_at',)


@admin.register(StatusHidden)
class StatusHiddenAdmin(admin.ModelAdmin):
    list_display = ('status', 'user', 'hidden_at')
    list_filter = ('hidden_at',)
    search_fields = ('user__username', 'status__user__username')
    readonly_fields = ('hidden_at',)
