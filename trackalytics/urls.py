"""
URL configuration for trackalytics project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from account.views import (
    home_view,
    category_summary,
    transaction_summary,
    category_spending_trend,
    saving_view,
    income_summary,
    account_category_analysis,
    transaction_summary_by_category
)
from user.views import (
    login_view,
    logout_view,
    register_view
)

urlpatterns = [
    path("", home_view, name='home_view'),
    path('summary/', category_summary, name='category_summary'),
    path('transaction/', transaction_summary, name='transaction'),
    path('category_transaction/', transaction_summary_by_category, name='category_transaction'),
    path('trend/', category_spending_trend, name='trend'),
    path('saving/', saving_view, name='saving'),
    path('income/', income_summary, name='income'),
    path('analysis/', account_category_analysis, name='analysis'),
    path('admin/', admin.site.urls),
    path("login/", login_view, name='login'),
    path("logout/", logout_view, name='logout'),
    path("register/", register_view, name='register'),
]
