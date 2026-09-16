def area_ativa(request):
    """
    Disponibiliza `area_ativa` (produção/predial) e `pode_alternar_area` em
    todos os templates. Administradores e staff podem alternar a área que
    estão visualizando (guardada na sessão); os demais usuários sempre veem
    a própria área cadastrada.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    pode_alternar = bool(getattr(user, 'is_staff', False) or getattr(user, 'tipo_acesso', None) == 'administrador')

    if pode_alternar:
        area = request.session.get('area_ativa') or getattr(user, 'area', None) or 'producao'
    else:
        area = getattr(user, 'area', None)

    return {
        'area_ativa': area,
        'pode_alternar_area': pode_alternar,
    }
