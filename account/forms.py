from django import forms
import os

class CategoryForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    VIEW_CHOICES = [
        ('chart', 'Chart View'),
        ('table', 'Tabular View')
    ]
    view_type = forms.ChoiceField(choices=VIEW_CHOICES, required=False, initial='chart')

class SpecificCategoryForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    category = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        categories = kwargs.pop("categories", [])
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = [("", "All Categories")] + [(c, c) for c in categories]

class DateRangeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

class CategoryTrendForm(forms.Form):
    GROUP_BY_CHOICES = [
        ("month", "Month"),
        ("year", "Year"),
    ]

    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    group_by = forms.ChoiceField(choices=GROUP_BY_CHOICES)