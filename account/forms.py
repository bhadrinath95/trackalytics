from django import forms

class CategoryForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    VIEW_CHOICES = [
        ('chart', 'Chart View'),
        ('table', 'Tabular View')
    ]
    view_type = forms.ChoiceField(choices=VIEW_CHOICES, required=False, initial='chart')

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