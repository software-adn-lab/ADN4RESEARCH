import behave.runner
from behave import *

use_step_matcher("re")


@step('que la fase de "selección" inicia el "(?P<fecha_inicio>.+)" y finaliza el "(?P<fecha_fin>.+)"')
def step_impl(context, fecha_inicio, fecha_fin):
    pass


@step('hoy es "(?P<fecha_actual>.+)"')
def step_impl(context, fecha_actual):
    pass


@step("consulte la información del proyecto")
def step_impl(context):
    pass


@step('el sistema debe operar en modo "(?P<modo>.+)"')
def step_impl(context, modo):
    pass


@step('deben estar habilitadas las acciones "(?P<acciones_habilitadas>.+)"')
def step_impl(context, acciones_habilitadas):
    pass