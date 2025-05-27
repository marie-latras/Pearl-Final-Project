# todo/admin.py
from django.contrib import admin
from .models import Task
from django.contrib.admin.actions import delete_selected

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'completed', 'created_at')  # Fields to display in the list view
    list_filter = ('completed', 'user', 'created_at')  # Filters on the right side
    search_fields = ('title', 'description')  # Searchable fields
    actions = [delete_selected]  # Explicitly include the delete action

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Optionally customize the delete action's verbose name
        if 'delete_selected' in actions:
            actions['delete_selected'].short_description = 'Delete selected tasks'
        return actions

    # Optional: Customize the delete confirmation message
    def get_deleted_objects(self, objs, request):
        deleted_objects, model_count, perms_needed = super().get_deleted_objects(objs, request)
        return deleted_objects, model_count, perms_needed