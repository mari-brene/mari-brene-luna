"""A Luna fala a hora do usuário, não a do servidor (que roda em UTC)."""

from datetime import datetime, timezone

import pytest

from luna.core import relogio

# 25/11/2026 02:30 em UTC == 24/11/2026 23:30 em Brasília
INSTANTE_UTC = datetime(2026, 11, 25, 2, 30, tzinfo=timezone.utc)


class RelogioFixo(datetime):
    @classmethod
    def now(cls, tz=None):
        return INSTANTE_UTC.astimezone(tz) if tz else INSTANTE_UTC.replace(tzinfo=None)


@pytest.fixture(autouse=True)
def servidor_em_utc(monkeypatch):
    monkeypatch.setattr(relogio, "datetime", RelogioFixo)
    monkeypatch.delenv("LUNA_FUSO", raising=False)
    relogio.fuso.cache_clear()
    yield
    relogio.fuso.cache_clear()


def test_agora_esta_no_fuso_de_brasilia():
    assert relogio.agora().strftime("%d/%m %H:%M") == "24/11 23:30"


def test_hora_e_data_faladas_corretas(luna, sessao):
    assert "23h30" in luna.processar("que horas são", sessao).texto
    assert "24 de novembro" in luna.processar("que dia é hoje", sessao).texto  # ainda não virou o dia


def test_lembrete_salva_com_horario_local(luna, sessao):
    luna.processar("lembrar de dormir cedo", sessao)
    assert "24/11 23:30" in luna.processar("ver lembretes", sessao).texto


def test_ia_recebe_o_horario_local():
    from luna.ia import _agora
    assert _agora() == "terça-feira, 24/11/2026 23:30"


def test_fuso_configuravel(monkeypatch):
    monkeypatch.setenv("LUNA_FUSO", "Europe/Lisbon")
    relogio.fuso.cache_clear()
    assert relogio.agora().strftime("%H:%M") == "02:30"


def test_fuso_invalido_cai_para_brasilia(monkeypatch):
    monkeypatch.setenv("LUNA_FUSO", "Marte/Olympus_Mons")
    relogio.fuso.cache_clear()
    assert relogio.agora().strftime("%H:%M") == "23:30"
