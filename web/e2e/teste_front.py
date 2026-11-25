"""
Teste ponta a ponta do front da Luna no Chrome (Playwright).

- Front: o build de produção (web/dist), servido via page.route.
- API: o ServicoLuna REAL (Python) respondendo às rotas /api/* — sem FastAPI,
  sem servidor, sem internet.
- Voz: speechSynthesis e SpeechRecognition simulados.

Como rodar (na raiz do repositório):
    cd web && npm run build && cd ..
    pip install playwright && playwright install chromium
    python web/e2e/teste_front.py

Capturas de tela ficam em web/e2e/capturas/.
"""
import json
import mimetypes
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
os.environ["LUNA_DB"] = str(Path(tempfile.mkdtemp()) / "e2e.db")

from playwright.sync_api import expect, sync_playwright  # noqa: E402

from luna.web.servico import FraseInvalida, ServicoLuna  # noqa: E402

BUILD = Path(os.environ.get("LUNA_BUILD", RAIZ / "web" / "dist"))
SHOTS = Path(__file__).resolve().parent / "capturas"
SHOTS.mkdir(exist_ok=True)
servico = ServicoLuna()
estado = {"api_fora": False, "segurar": False, "presas": [], "chamadas": 0}

MOCKS = r"""
window.__falado = [];
window.__abertos = [];
window.__mic = [];
window.__micAberto = 0;
window.SpeechSynthesisUtterance = class { constructor(t) { this.text = t; } };
Object.defineProperty(window, "speechSynthesis", { value: {
  speak(u) { window.__falado.push({ t: u.text, l: u.lang }); setTimeout(() => u.onend && u.onend(), 5); },
  cancel() {}, getVoices() { return []; },
}});
window.open = (u) => { window.__abertos.push(u); return null; };
Object.defineProperty(window, "Notification", { value: class { static permission = "denied"; static requestPermission() { return Promise.resolve("denied"); } } });
window.SpeechRecognition = window.webkitSpeechRecognition = class {
  start() {
    window.__micAberto++;
    window.__ultimoLang = this.lang;
    const frase = window.__mic.shift();
    setTimeout(() => {
      if (!frase) return; // fica "ouvindo" até stop()
      this.onresult && this.onresult({ resultIndex: 0, results: [{ isFinal: false, 0: { transcript: frase.slice(0, 5) } }] });
      setTimeout(() => {
        this.onresult && this.onresult({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: frase } }] });
        this.onend && this.onend();
      }, 60);
    }, 60);
  }
  stop() { this.onend && this.onend(); }
  abort() {}
};
"""


def servir_front(route):
    caminho = route.request.url.split("luna.test", 1)[1].split("?")[0]
    arquivo = BUILD / (caminho.lstrip("/") or "index.html")
    if not arquivo.is_file():
        arquivo = BUILD / "index.html"
    tipo = mimetypes.guess_type(arquivo.name)[0] or "text/html"
    route.fulfill(status=200, body=arquivo.read_bytes(), content_type=tipo)


def api(route):
    if estado["segurar"] and route.request.method == "POST":
        estado["presas"].append(route)  # simula o servidor dormindo: responde depois
        return
    estado["chamadas"] += 1
    if estado["api_fora"]:
        return route.abort("connectionrefused")
    req = route.request
    cors = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type"}
    if req.method == "OPTIONS":
        return route.fulfill(status=204, headers={**cors, "Access-Control-Allow-Methods": "GET,POST"})
    corpo = json.loads(req.post_data or "{}") if req.method == "POST" else {}
    caminho = req.url.split("8000", 1)[1]
    try:
        if caminho == "/api/sessoes":
            dados = servico.iniciar(corpo.get("sessao_id"))
        elif caminho == "/api/comando":
            dados = servico.comando(corpo.get("frase", ""), corpo.get("sessao_id"))
        elif caminho == "/api/habilidades":
            dados = servico.habilidades()
        else:
            return route.fulfill(status=404, headers=cors, body="{}")
    except FraseInvalida as e:
        return route.fulfill(status=422, headers=cors, content_type="application/json", body=json.dumps({"detail": str(e)}))
    route.fulfill(status=200, headers=cors, content_type="application/json", body=json.dumps(dados))


def ultima_luna(page):
    return page.locator(".linha-luna .balao").last


def enviar(page, frase):
    n = page.locator(".linha-luna").count()
    page.get_by_label("Mensagem para a Luna").fill(frase)
    page.get_by_label("Mensagem para a Luna").press("Enter")
    expect(page.locator(".linha-luna:not(:has(.digitando))")).to_have_count(n + 1, timeout=5000)
    return ultima_luna(page).inner_text()


def ok(msg):
    print(f"  ✔ {msg}")


with sync_playwright() as p:
    assert (BUILD / "index.html").is_file(), f"build não encontrado em {BUILD}: rode 'npm run build' em web/"
    nav = p.chromium.launch(executable_path=os.environ.get("CHROME") or None)
    ctx = nav.new_context(viewport={"width": 1280, "height": 820}, locale="pt-BR")
    ctx.add_init_script(MOCKS)
    ctx.route("http://luna.test/**", servir_front)
    ctx.route("http://localhost:8000/**", api)
    page = ctx.new_page()
    erros = []
    page.on("console", lambda m: m.type == "error" and erros.append(m.text))
    page.on("pageerror", lambda e: erros.append(str(e)))

    print("1. carregar")
    page.goto("http://luna.test/")
    expect(page.locator(".status-online")).to_be_visible()
    expect(page.locator(".linha-luna")).to_have_count(1)
    expect(page.locator(".sugestoes button")).to_have_count(5)
    assert "terminal" not in page.locator(".linha-luna").first.inner_text()
    sid = page.evaluate("localStorage.getItem('luna:sessao')")
    assert sid and len(sid) >= 16
    assert page.evaluate("window.__falado.length") == 0  # sem gesto do usuário o Chrome não deixa falar
    ok(f"saudação exibida (não falada antes da interação), sessão {sid[:6]}…")
    page.screenshot(path=SHOTS / "1-inicio.png")

    print("2. sugestão")
    page.get_by_role("button", name="Que horas são?").click()
    expect(page.locator(".linha-voce")).to_have_count(1)
    expect(page.locator(".linha-luna")).to_have_count(2)
    expect(page.locator(".sugestoes")).to_have_count(0)
    page.wait_for_function("window.__falado.length >= 1")
    ok(f"resposta falada: {ultima_luna(page).inner_text().splitlines()[0]}")

    print("3. ação abrir_url")
    enviar(page, "tocar Queen")
    expect(ultima_luna(page).get_by_role("link", name="Abrir no Spotify ↗")).to_have_attribute("href", "https://open.spotify.com/search/Queen")
    assert page.evaluate("window.__abertos") == ["https://open.spotify.com/search/Queen"]
    ok("link na mensagem + window.open chamado")

    print("4. timer dispara")
    enviar(page, "timer de 2 segundos")
    expect(page.locator(".timer")).to_have_count(1)
    texto_timer = page.locator(".timer-tempo").inner_text()
    assert texto_timer in ("00:02", "00:01"), texto_timer
    expect(page.locator(".timer")).to_have_count(0, timeout=4000)
    expect(ultima_luna(page)).to_contain_text("⏰")
    ok(f"contagem {texto_timer}, disparou: {ultima_luna(page).inner_text().splitlines()[0]}")

    print("5. cancelar timers")
    enviar(page, "timer de 10 minutos")
    enviar(page, "iniciar pomodoro")
    expect(page.locator(".timer")).to_have_count(3)
    assert page.locator(".timer-tempo").first.inner_text() in ("10:00", "09:59")
    page.screenshot(path=SHOTS / "2-timers.png")
    page.get_by_label("Cancelar timer").first.click()
    expect(page.locator(".timer")).to_have_count(2)
    enviar(page, "cancelar timer")
    expect(page.locator(".timer")).to_have_count(0)
    ok("cancelar um (botão) e todos (comando)")

    print("6. pergunta pendente por texto")
    r = enviar(page, "criar lembrete")
    assert "lembrete" in r.lower() or "anoto" in r.lower(), r
    enviar(page, "comprar pão")
    assert "comprar pão" in enviar(page, "ver lembretes")
    ok("pergunta → resposta → salvo")

    print("7. voz")
    page.evaluate("window.__mic.push('lembrar de estudar React')")
    page.get_by_label("Falar com a Luna").click()
    expect(page.locator(".status")).to_contain_text("ouvindo")
    expect(page.locator(".linha-voce").last).to_contain_text("lembrar de estudar React", timeout=5000)
    expect(ultima_luna(page)).to_contain_text("estudar React")
    expect(page.get_by_label("Falar com a Luna")).to_be_visible()
    ok("microfone → frase → resposta, microfone volta ao normal")

    print("8. voz com pergunta: microfone reabre sozinho")
    antes = page.evaluate("window.__micAberto")
    page.evaluate("window.__mic.push('criar lembrete', 'revisar o PR')")
    page.get_by_label("Falar com a Luna").click()
    expect(page.locator(".linha-voce").last).to_contain_text("revisar o PR", timeout=6000)
    expect(ultima_luna(page)).to_contain_text("revisar o PR")
    assert page.evaluate("window.__micAberto") == antes + 2
    ok("2 escutas com 1 clique")

    print("9. tradução: escuta em inglês")
    page.evaluate("window.__mic.push('traduzir para o português', 'good morning')")
    page.get_by_label("Falar com a Luna").click()
    expect(page.locator(".linha-voce").last).to_contain_text("good morning", timeout=6000)
    assert page.evaluate("window.__ultimoLang") == "en-US"
    expect(ultima_luna(page)).not_to_contain_text("Deu ruim")
    ok(f"segunda escuta em en-US → {ultima_luna(page).inner_text().splitlines()[0]}")

    print("10. parar microfone")
    page.get_by_label("Falar com a Luna").click()
    expect(page.get_by_label("Parar de ouvir")).to_be_visible()
    page.get_by_label("Parar de ouvir").click()
    expect(page.get_by_label("Falar com a Luna")).to_be_visible()
    ok("clique de novo para de ouvir")

    print("11. comando de desktop na web")
    r = enviar(page, "desligar o computador em 1 hora")
    assert "desktop" in r.lower(), r
    ok(r.splitlines()[0])

    print("12. ajuda")
    page.get_by_label("O que a Luna sabe fazer").click()
    expect(page.locator("dialog.ajuda")).to_be_visible()
    itens = page.locator("dialog.ajuda li").count()
    assert itens >= 15
    assert page.locator("dialog.ajuda").get_by_text("Abrir Discord").count() == 0
    page.screenshot(path=SHOTS / "3-ajuda.png")
    page.locator("dialog.ajuda li button", has_text="Conta piada").click()
    expect(page.locator("dialog.ajuda")).to_be_hidden()
    expect(page.locator(".linha-voce").last).to_contain_text("Conta uma piada")
    expect(page.locator(".digitando")).to_have_count(0)
    page.wait_for_timeout(300)
    ok(f"{itens} habilidades, clique envia o exemplo")

    print("13. mudo")
    falado = page.evaluate("window.__falado.length")
    page.get_by_label("Silenciar a Luna").click()
    enviar(page, "que dia é hoje")
    assert page.evaluate("window.__falado.length") == falado
    assert page.evaluate("localStorage.getItem('luna:mudo')") == "1"
    page.get_by_label("Ativar voz da Luna").click()
    ok("silenciado não fala; preferência salva")

    print("14. recarregar mantém sessão e lembretes")
    page.reload()
    expect(page.locator(".status-online")).to_be_visible()
    assert page.evaluate("localStorage.getItem('luna:sessao')") == sid
    r = enviar(page, "ver lembretes")
    assert "comprar pão" in r and "revisar o PR" in r
    ok("mesma sessão após reload")

    print("15. outro navegador = outro usuário")
    pagina2 = ctx.browser.new_context(locale="pt-BR")
    pagina2.add_init_script(MOCKS)
    pagina2.route("http://luna.test/**", servir_front)
    pagina2.route("http://localhost:8000/**", api)
    p2 = pagina2.new_page()
    p2.goto("http://luna.test/")
    expect(p2.locator(".status-online")).to_be_visible()
    r2 = enviar(p2, "ver lembretes")
    assert "comprar pão" not in r2
    pagina2.close()
    ok("lembretes isolados")

    print("16. servidor fora do ar")
    estado["api_fora"] = True
    page.get_by_label("Mensagem para a Luna").fill("oi")
    page.get_by_label("Mensagem para a Luna").press("Enter")
    expect(page.locator(".aviso-erro")).to_be_visible()
    expect(page.locator(".status-offline")).to_be_visible()
    expect(page.get_by_label("Mensagem para a Luna")).to_be_disabled()
    page.screenshot(path=SHOTS / "4-offline.png")
    estado["api_fora"] = False
    qtd_luna = page.locator(".linha-luna").count()
    page.get_by_role("button", name="Tentar de novo").click()
    expect(page.locator(".status-online")).to_be_visible()
    page.wait_for_timeout(300)
    assert page.locator(".linha-luna").count() == qtd_luna, "reconectar repetiu a saudação"
    expect(page.locator(".aviso-erro")).to_have_count(0)
    ok("banner offline e reconexão")

    print("17. servidor acordando")
    estado["segurar"] = True
    page.get_by_label("Mensagem para a Luna").fill("que horas são")
    page.get_by_label("Mensagem para a Luna").press("Enter")
    expect(page.locator(".aviso-info")).to_contain_text("dormindo", timeout=6000)
    expect(page.locator(".status")).to_contain_text("acordando")
    page.screenshot(path=SHOTS / "7-acordando.png")
    estado["segurar"] = False
    for presa in estado["presas"]:
        api(presa)
    estado["presas"].clear()
    expect(page.locator(".aviso-info")).to_have_count(0)
    expect(ultima_luna(page)).to_contain_text("h")
    expect(page.locator(".status")).to_contain_text("online")
    ok("aviso de 'acordando' aparece após 3,5 s e some com a resposta")

    print("18. celular")
    page.set_viewport_size({"width": 390, "height": 780})
    page.wait_for_timeout(300)
    largura = page.evaluate("document.documentElement.scrollWidth")
    assert largura <= 390, largura
    page.screenshot(path=SHOTS / "5-celular.png")
    ok("sem rolagem horizontal em 390px")

    page.set_viewport_size({"width": 1280, "height": 820})
    enviar(page, "oi")
    page.screenshot(path=SHOTS / "6-conversa.png")
    # horário nunca sobrepõe o texto do balão
    for balao in page.locator(".balao:not(.digitando)").all():
        caixa_p = balao.locator("p").last.bounding_box()
        caixa_h = balao.locator(".hora").bounding_box()
        assert caixa_h["y"] >= caixa_p["y"] + caixa_p["height"] - 1, "horário sobre o texto"
    nav.close()

    erros = [e for e in erros if "ERR_CONNECTION_REFUSED" not in e and "Failed to load resource" not in e]
    assert not erros, erros
    print(f"\nTUDO OK — {estado['chamadas']} chamadas à API, sem erros no console")
