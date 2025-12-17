"""
Behave environment configuration for Django integration.
"""
import os
import sys
import django
from django.test.utils import setup_test_environment
from django.db import connection

def before_all(context):
    # behave-django YA inicializó Django por ti aquí.
    pass 

def after_all(context):
    pass