from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Student, HealthRecord, FitnessPerformance

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'roll_number', 'section', 'parent', 'teacher']
    search_fields = ['name', 'roll_number']

from django import forms

class HealthRecordForm(forms.ModelForm):
    height = forms.FloatField(label="Height (cm)", required=False)
    weight = forms.FloatField(label="Weight (kg)", required=False)

    class Meta:
        model = HealthRecord
        fields = ['student', 'height', 'weight', 'activity_record', 'fitness_test_scores']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['height'].initial = self.instance.height
            self.fields['weight'].initial = self.instance.weight

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.height = self.cleaned_data.get('height')
        instance.weight = self.cleaned_data.get('weight')
        if commit:
            instance.save()
        return instance

@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):
    form = HealthRecordForm
    list_display = ['student', 'display_height', 'display_weight', 'display_bmi', 'fitness_status', 'updated_at']
    readonly_fields = ['display_bmi', 'fitness_status', 'ai_recommendations']

    def display_height(self, obj):
        return f"{obj.height} cm"
    display_height.short_description = "Height"

    def display_weight(self, obj):
        return f"{obj.weight} kg"
    display_weight.short_description = "Weight"

    def display_bmi(self, obj):
        return obj.bmi
    display_bmi.short_description = "BMI"




@admin.register(FitnessPerformance)
class FitnessPerformanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'metric_name', 'score', 'date']
    list_filter = ['metric_name', 'date']

admin.site.register(User, CustomUserAdmin)
