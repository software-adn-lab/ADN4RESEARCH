"""
Step definitions for F_EM_002-Manejar_tags_inductivos.feature
"""
from behave import given, when, then, step

use_step_matcher("re")


# =============================================================================
# HELPERS
# =============================================================================

def get_user_id(context, user_name: str) -> int:
    """Obtiene o crea un ID de usuario por nombre"""
    if user_name not in context.users:
        # Asignar IDs fijos para usuarios conocidos
        user_ids = {
            'Juan': 10,
            'Ana': 20,
            'Owner': 1
        }
        context.users[user_name] = user_ids.get(user_name, hash(user_name) % 1000)
    return context.users[user_name]


# =============================================================================
# ESCENARIO 1: Crear tag inductivo personal
# =============================================================================

@given('que el Investigador "(?P<user_name>.+)" está extrayendo datos de un estudio')
def step_researcher_extracting(context, user_name):
    """
    Setup: El investigador está trabajando en una extracción.
    """
    from apps.extraction.core.models import PaperExtraction
    
    user_id = get_user_id(context, user_name)
    
    # Crear una extracción asignada al investigador
    extraction = PaperExtraction.objects.create(
        study_id=1,
        project_id=context.project_id,
        assigned_to_id=user_id
    )
    context.current_extraction = extraction
    context.current_user = user_name
    context.current_user_id = user_id


@when('"(?P<user_name>.+)" crea un nuevo tag inductivo llamado "(?P<tag_name>.+)"')
def step_create_inductive_tag(context, user_name, tag_name):
    """
    El investigador crea un tag inductivo.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    user_id = get_user_id(context, user_name)
    
    tag = service.create_inductive_tag(
        project_id=context.project_id,
        name=tag_name,
        user_id=user_id
    )
    
    context.created_tag = tag
    context.tags[tag_name] = tag


@then(u"se debe registrar el tag con:")
def step_verify_tag_registration(context):
    """
    Verifica los atributos del tag creado según la tabla del feature.
    """
    from apps.extraction.taxonomy.models import Tag
    
    tag = context.created_tag
    
    # Parsear la tabla del feature
    for row in context.table:
        expected_name = row['Nombre']
        expected_owner = row['Propietario']
        expected_status = row['Estado']
        expected_visibility = row['Visibilidad']
        
        # Verificar nombre
        assert tag.name == expected_name, \
            f"Nombre esperado: {expected_name}, obtenido: {tag.name}"
        
        # Verificar propietario
        expected_owner_id = get_user_id(context, expected_owner)
        assert tag.created_by_id == expected_owner_id, \
            f"Propietario esperado: {expected_owner} (ID: {expected_owner_id}), obtenido: {tag.created_by_id}"
        
        # Verificar estado
        status_map = {
            'Pendiente de Aprobación': Tag.ApprovalStatus.PENDING,
            'Aprobado': Tag.ApprovalStatus.APPROVED,
            'Rechazado': Tag.ApprovalStatus.REJECTED
        }
        expected_status_value = status_map.get(expected_status)
        assert tag.approval_status == expected_status_value, \
            f"Estado esperado: {expected_status}, obtenido: {tag.approval_status}"
        
        # Verificar visibilidad
        expected_public = (expected_visibility == 'Pública')
        assert tag.is_public == expected_public, \
            f"Visibilidad esperada: {expected_visibility} (is_public={expected_public}), obtenido: is_public={tag.is_public}"


@then('el tag "(?P<tag_name>.+)" debe estar disponible para ser usado por "(?P<user_name>.+)" en otros papers')
def step_tag_available_for_user(context, tag_name, user_name):
    """
    Verifica que el tag esté disponible para el usuario indicado.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    user_id = get_user_id(context, user_name)
    
    visible_tags = service.get_visible_tags_for_user(context.project_id, user_id)
    visible_names = [t['name'] for t in visible_tags]
    
    assert tag_name in visible_names, \
        f"El tag '{tag_name}' no está disponible para {user_name}. Tags visibles: {visible_names}"


@then('el tag "(?P<tag_name>.+)" NO debe aparecer en la lista de tags del Investigador "(?P<user_name>.+)"')
def step_tag_not_visible_for_user(context, tag_name, user_name):
    """
    Verifica que el tag NO esté visible para otro usuario.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    user_id = get_user_id(context, user_name)
    
    visible_tags = service.get_visible_tags_for_user(context.project_id, user_id)
    visible_names = [t['name'] for t in visible_tags]
    
    assert tag_name not in visible_names, \
        f"El tag '{tag_name}' NO debería estar visible para {user_name}, pero aparece en: {visible_names}"


# =============================================================================
# ESCENARIO 2: Moderación de tags por Owner
# =============================================================================

@given('que existe un tag "(?P<tag_name>.+)" propuesto por "(?P<user_name>.+)" con estado "Pendiente de Aprobación"')
def step_existing_pending_tag(context, tag_name, user_name):
    """
    Setup: Existe un tag pendiente de aprobación.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    user_id = get_user_id(context, user_name)
    
    tag = service.create_inductive_tag(
        project_id=context.project_id,
        name=tag_name,
        user_id=user_id
    )
    
    context.pending_tag = tag
    context.tags[tag_name] = tag


@when("el Owner decide (?P<action>.+) la propuesta")
def step_owner_decides(context, action):
    """
    El Owner aprueba o rechaza el tag.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    owner_id = get_user_id(context, 'Owner')
    
    action_normalized = action.strip().lower()
    
    if action_normalized == 'aprobar':
        context.moderated_tag = service.approve_tag(context.pending_tag.id, owner_id)
    elif action_normalized == 'rechazar':
        context.moderated_tag = service.reject_tag(context.pending_tag.id, owner_id)
    else:
        raise ValueError(f"Acción desconocida: {action}")


@then('el estado del tag cambia a "(?P<expected_status>.+)"')
def step_verify_tag_status(context, expected_status):
    """
    Verifica el nuevo estado del tag.
    """
    from apps.extraction.taxonomy.models import Tag
    
    tag = context.moderated_tag
    
    status_map = {
        'Aprobado': Tag.ApprovalStatus.APPROVED,
        'Rechazado': Tag.ApprovalStatus.REJECTED,
        'Pendiente de Aprobación': Tag.ApprovalStatus.PENDING
    }
    
    expected = status_map.get(expected_status)
    
    assert tag.approval_status == expected, \
        f"Estado esperado: {expected_status} ({expected}), obtenido: {tag.approval_status}"


@then(r'la visibilidad para el resto del equipo \(ej\. "(?P<other_user>.+)"\) pasa a ser "(?P<expected_visibility>.+)"')
def step_verify_team_visibility(context, other_user, expected_visibility):
    """
    Verifica la visibilidad del tag para otros miembros del equipo.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    other_user_id = get_user_id(context, other_user)
    
    tag_name = context.moderated_tag.name
    visible_tags = service.get_visible_tags_for_user(context.project_id, other_user_id)
    visible_names = [t['name'] for t in visible_tags]
    
    is_visible = tag_name in visible_names
    expected_public = (expected_visibility == 'Pública')
    
    if expected_public:
        assert is_visible, \
            f"El tag '{tag_name}' debería ser visible para {other_user} (Pública), pero no lo es"
    else:
        assert not is_visible, \
            f"El tag '{tag_name}' NO debería ser visible para {other_user} (Privada), pero sí lo es"


# =============================================================================
# ESCENARIO 3: Fusión de tags duplicados
# =============================================================================

@given(u"la existencia de los siguientes tags propuestos pendientes:")
def step_setup_pending_tags(context):
    """
    Crea múltiples tags pendientes según la tabla del feature.
    """
    from apps.extraction.taxonomy.services import TagService
    from apps.extraction.core.models import PaperExtraction, Quote
    
    service = TagService()
    
    for row in context.table:
        tag_name = row['Nombre_Tag']
        owner_name = row['Propietario']
        user_id = get_user_id(context, owner_name)
        
        # Crear tag inductivo
        tag = service.create_inductive_tag(
            project_id=context.project_id,
            name=tag_name,
            user_id=user_id
        )
        context.tags[tag_name] = tag
        
        # Crear una extracción y quote para simular uso del tag
        extraction = PaperExtraction.objects.create(
            study_id=100 + user_id,  # ID único por usuario
            project_id=context.project_id,
            assigned_to_id=user_id
        )
        
        quote = Quote.objects.create(
            paper_extraction=extraction,
            text_portion=f"Cita usando el tag {tag_name}",
            researcher_id=user_id
        )
        quote.tags.add(tag)
        
        context.quotes[f"{owner_name}_{tag_name}"] = quote


@when('el Owner aprueba "(?P<approved_tag>.+)" y lo marca como equivalente a "(?P<duplicate_tag>.+)"')
def step_owner_approves_and_merges(context, approved_tag, duplicate_tag):
    """
    El Owner aprueba un tag y fusiona el duplicado.
    """
    from apps.extraction.taxonomy.services import TagService
    
    service = TagService()
    owner_id = get_user_id(context, 'Owner')
    
    # Primero aprobar el tag principal
    tag_to_approve = context.tags[approved_tag]
    service.approve_tag(tag_to_approve.id, owner_id)
    
    # Luego fusionar el duplicado
    duplicate = context.tags[duplicate_tag]
    service.merge_tags(tag_to_approve.id, duplicate.id, owner_id)
    
    context.approved_tag_name = approved_tag
    context.merged_tag_name = duplicate_tag


@then('ambos tags se fusionan en un único tag global "(?P<final_tag_name>.+)"')
def step_verify_merge_result(context, final_tag_name):
    """
    Verifica que los tags se hayan fusionado correctamente.
    """
    from apps.extraction.taxonomy.models import Tag
    
    # El tag fusionado debe tener merged_into apuntando al aprobado
    merged_tag = context.tags[context.merged_tag_name]
    merged_tag.refresh_from_db()
    
    approved_tag = context.tags[final_tag_name]
    approved_tag.refresh_from_db()
    
    assert merged_tag.merged_into == approved_tag, \
        f"El tag '{context.merged_tag_name}' debería estar fusionado en '{final_tag_name}'"
    
    assert approved_tag.is_public, \
        f"El tag '{final_tag_name}' debería ser público después de aprobarse"
    
    assert approved_tag.approval_status == Tag.ApprovalStatus.APPROVED, \
        f"El tag '{final_tag_name}' debería estar aprobado"


@then('las extracciones que "(?P<user_name>.+)" hizo con "(?P<old_tag>.+)" ahora deben estar asociadas al tag aprobado "(?P<new_tag>.+)"')
def step_verify_quote_reassignment(context, user_name, old_tag, new_tag):
    """
    Verifica que las quotes se hayan reasignado al tag correcto.
    """
    # Obtener la quote que Ana creó
    quote_key = f"{user_name}_{old_tag}"
    quote = context.quotes[quote_key]
    quote.refresh_from_db()
    
    # Verificar que el nuevo tag esté asociado
    approved_tag = context.tags[new_tag]
    quote_tags = list(quote.tags.all())
    
    assert approved_tag in quote_tags, \
        f"La quote de {user_name} debería tener el tag '{new_tag}'. Tags actuales: {[t.name for t in quote_tags]}"
    
    # Verificar que el tag viejo ya no esté (fue reemplazado)
    old_tag_obj = context.tags[old_tag]
    assert old_tag_obj not in quote_tags, \
        f"La quote de {user_name} NO debería tener el tag fusionado '{old_tag}'"
