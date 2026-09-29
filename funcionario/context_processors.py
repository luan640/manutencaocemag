def get_area_ativa(request):
    """
    Retorna a área (produção/predial) que o usuário está visualizando no momento.
    Administradores e staff podem alternar a área via `alternar_area` (guardada
    na sessão); os demais usuários sempre operam na própria área cadastrada.

    Views que criam ou filtram registros por área devem usar esta função em vez
    de `request.user.area` diretamente, pois esse campo reflete a área fixa do
    funcionário e não o painel que ele está visualizando no momento.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None

    pode_alternar = bool(getattr(user, 'is_staff', False) or getattr(user, 'tipo_acesso', None) == 'administrador')

    if pode_alternar:
        return request.session.get('area_ativa') or getattr(user, 'area', None) or 'producao'
    return getattr(user, 'area', None)


def area_ativa(request):
    """
    Disponibiliza `area_ativa` (produção/predial) e `pode_alternar_area` em
    todos os templates.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    pode_alternar = bool(getattr(user, 'is_staff', False) or getattr(user, 'tipo_acesso', None) == 'administrador')

    return {
        'area_ativa': get_area_ativa(request),
        'pode_alternar_area': pode_alternar,
    }
