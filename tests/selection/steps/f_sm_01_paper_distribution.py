import behave.runner
from behave import *

use_step_matcher("re")


@step("investigadores con cargas horarias definidas:")
def step_impl(context):
    pass


@step("papers con un número específico de hojas:")
def step_impl(context):
    pass


@step("que cada paper debe asignarse (?P<total_revisiones_paper>.+) veces a revisores distintos")
def step_impl(context, total_revisiones_paper):
    pass


@step("cada paper debe tener (?P<total_revisiones_paper>.+) revisores distintos")
def step_impl(context, total_revisiones_paper):
    pass


@step("ningún investigador debe recibir asignaciones repetidas del mismo paper")
def step_impl(context):
    pass


@step("la distribución resultante debe ser:")
def step_impl(context):
    pass