from django import forms
from .models import Status


class StatusForm(forms.ModelForm):
    """Form for creating a new status"""
    
    class Meta:
        model = Status
        fields = ['content', 'media', 'media_type']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white',
                'rows': 3,
                'placeholder': 'What\'s on your mind? (optional)',
                'maxlength': '500'
            }),
            'media': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600',
                'accept': 'image/*,video/*'
            }),
            'media_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        media = cleaned_data.get('media')
        
        # At least one of content or media must be provided
        if not content and not media:
            raise forms.ValidationError("Please provide either text or media for your status.")
        
        return cleaned_data
