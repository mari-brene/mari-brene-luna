from luna.web.sessoes import RepositorioSessoes, id_valido, novo_id


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_sem_id_cria_sessao_nova():
    repo = RepositorioSessoes()
    sessao, nova = repo.obter(None)
    assert nova and id_valido(sessao.id)


def test_mesmo_id_devolve_mesma_sessao():
    repo = RepositorioSessoes()
    a, _ = repo.obter(None)
    b, nova = repo.obter(a.id)
    assert b is a and not nova


def test_id_invalido_e_ignorado():
    repo = RepositorioSessoes()
    for ruim in ["", "curto", "tem espaço no meio aaaaaaaa", "../../etc/passwd", "x" * 65, "'; DROP TABLE--aaaa"]:
        sessao, nova = repo.obter(ruim)
        assert nova and sessao.id != ruim


def test_id_valido_desconhecido_e_reaproveitado():
    """Servidor reiniciou: o usuário volta com o mesmo ID e mantém os lembretes."""
    repo = RepositorioSessoes()
    antigo = novo_id()
    sessao, nova = repo.obter(antigo)
    assert nova and sessao.id == antigo


def test_sessao_expira_por_inatividade():
    relogio = Relogio()
    repo = RepositorioSessoes(ttl_segundos=60, relogio=relogio)
    a, _ = repo.obter(None)
    a.pendente = "algo"
    relogio.t = 61
    b, nova = repo.obter(a.id)
    assert nova and b is not a and b.pendente is None and b.id == a.id


def test_uso_renova_a_sessao():
    relogio = Relogio()
    repo = RepositorioSessoes(ttl_segundos=60, relogio=relogio)
    a, _ = repo.obter(None)
    for t in (50, 100, 150):
        relogio.t = t
        b, nova = repo.obter(a.id)
        assert b is a and not nova


def test_limite_descarta_a_menos_usada():
    repo = RepositorioSessoes(maximo=2)
    a, _ = repo.obter(None)
    b, _ = repo.obter(None)
    repo.obter(a.id)          # a passa a ser a mais recente
    repo.obter(None)          # estoura o limite: sai b
    assert len(repo) == 2
    _, nova_b = repo.obter(b.id)
    assert nova_b
