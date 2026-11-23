# Como rodar os testes

O BernoulliPay tem dois tipos de teste, rodados pelo mesmo `pytest`:

| Tipo | Onde fica | Quantos | O que faz |
|---|---|---:|---|
| Unidade e integração | `apps/*/tests.py`, `apps/*/test_*.py` | 261 | Regras de negócio, importação, telas pelo `django.test.Client`, comandos; mede a **cobertura** (mínimo de 80%) |
| End-to-end (E2E) | `e2e/` | 4 | Sobe o sistema e o usa num **Chromium de verdade** pelo Playwright: clica, envia planilha, responde ao `confirm()`, baixa o `.xlsx` |

O que cada teste garante, e por quê, está na seção 4 de [`TESTES.md`](TESTES.md).
Nenhum teste toca o `db.sqlite3`: cada execução cria um banco descartável.

---

## 1. Preparar o ambiente (uma vez por máquina)

```bash
python -m venv .venv
source .venv/bin/activate              # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt    # pytest, pytest-django, pytest-cov, pytest-xdist, pytest-playwright, ruff
python -m playwright install chromium  # o navegador dos E2E (~150 MB)
```

No Linux sem as bibliotecas do navegador, use
`python -m playwright install --with-deps chromium` (pede `sudo`).

Os comandos abaixo supõem o `.venv` ativado. Sem ativar, troque `pytest` por
`.venv/bin/python -m pytest`.

---

## 2. Testes de unidade e integração, com cobertura

```bash
pytest apps -n auto
```

- `-n auto` (pytest-xdist) divide os testes entre os núcleos da máquina: numa
  máquina de 4 núcleos leva **de 1 min 20 s a 2 min 40 s**, conforme a carga da
  máquina, contra 3 min 30 s ou mais sem ele. Sem ele também funciona, só
  demora mais.
- Ao final aparece a tabela de cobertura por arquivo (só os que **não** estão
  em 100%) e a linha que importa:

  ```
  Required test coverage of 80.0% reached. Total coverage: 96.16%
  261 passed, 58 subtests passed
  ```

  A contagem de subtestes (`58 subtests passed`) às vezes não aparece na
  linha final; eles rodam do mesmo jeito.

- Abaixo de 80% o comando **falha**, igual ao CI (`fail_under` em
  `pyproject.toml`).

Variações úteis:

```bash
pytest apps -n auto --cov-report=html      # também gera htmlcov/index.html, para abrir no navegador
pytest apps/imports --no-cov               # só um app
pytest apps/payroll/test_filters.py --no-cov -v   # um arquivo, um teste por linha
pytest apps --no-cov -x                    # para no primeiro erro
pytest apps --no-cov -k duplicate          # só os testes com "duplicate" no nome
python manage.py test -v2                  # o runner do Django, mostrando a docstring de cada teste
```

`--no-cov` é para quando se roda **só uma parte**: sem ele, a cobertura de um
pedaço da suíte fica abaixo de 80% e o comando reprova mesmo com todos os
testes verdes.

---

## 3. Testes E2E

### Sem janela (rápido, como no CI)

```bash
pytest e2e --no-cov
```

```
4 passed        # de 20 s a 1 min, conforme a máquina
```

### Ao vivo, com o navegador aberto

```bash
pytest e2e --no-cov --headed --slowmo 500
```

- `--headed` abre a janela do Chromium; `--slowmo 500` espera meio segundo
  entre uma ação e outra, para dar tempo de acompanhar. Os quatro levam de
  1 min 30 s a 2 min; aumente o número para ir mais devagar.
- **Não use `-n auto` aqui**: cada processo abriria a própria janela ao mesmo
  tempo.
- `--no-cov` é obrigatório: os E2E sozinhos cobrem pouco do código e o limite
  de 80% reprovaria a execução.

Um fluxo de cada vez:

```bash
pytest e2e/test_access.py       --no-cov --headed --slowmo 500   # login e acesso por cargo
pytest e2e/test_import.py       --no-cov --headed --slowmo 500   # importação de uma lista de pagamento
pytest e2e/test_payment_run.py  --no-cov --headed --slowmo 500   # cadastro → lançamento → resumo → Excel
pytest e2e/test_batch_delete.py --no-cov --headed --slowmo 500   # exclusão de importações em lote
```

Quando um E2E falha, `--screenshot only-on-failure` guarda a captura da tela
em `test-results/` (fora do Git).

### Onde a janela aparece

- **Windows, macOS, Linux com desktop:** abre normalmente.
- **WSL 2 no Windows 11:** abre no Windows pelo WSLg, sem configurar nada
  (confira com `echo $DISPLAY`, que deve mostrar `:0`).
- **Sem tela** (SSH, container): rode sem `--headed`.

---

## 4. A suíte inteira, como o CI roda

```bash
ruff check .
pytest -n auto
```

`pytest` sem caminho roda `apps/` e `e2e/` juntos (os `testpaths` do
`pyproject.toml`), com cobertura: **265 testes, 96%, de 1 min 30 s a 3 min** em 4
núcleos, conforme a carga da máquina. O GitHub Actions faz exatamente isso a cada push na `main` e em todo
pull request (`.github/workflows/ci.yml`), depois de instalar o Chromium.

---

## 5. Roteiro para a apresentação

| Parte | Comando | O que mostrar |
|---|---|---|
| 1. Unidade/integração e cobertura | `pytest apps -n auto` | Os 261 verdes e a linha `Total coverage: 96%` acima do mínimo de 80% |
| 2. E2E | `pytest e2e --no-cov --headed --slowmo 500` | A janela do Chromium fazendo os quatro fluxos sozinha |

Antes da apresentação, rode os dois uma vez na máquina que vai ser usada: a
primeira execução do Chromium demora mais, e é a hora de descobrir se falta o
`playwright install`. Feche os outros programas antes: com a máquina ocupada
os tempos chegam a dobrar.

---

## 6. Problemas comuns

| Sintoma | Causa | O que fazer |
|---|---|---|
| `FAIL Required test coverage of 80% not reached` rodando só uma parte | A cobertura é medida sobre `apps/` inteiro | Acrescente `--no-cov` |
| `Executable doesn't exist` / `playwright install` na mensagem de erro | O Chromium do Playwright não foi baixado | `python -m playwright install chromium` |
| Erro de bibliotecas do sistema ao abrir o Chromium (Linux) | Faltam dependências do navegador | `python -m playwright install --with-deps chromium` |
| `--headed` falha com erro de display | Máquina sem tela | Rode sem `--headed` |
| `error: unrecognized arguments: -n` | `pytest-xdist` não instalado | `pip install -r requirements-dev.txt` |
| `ModuleNotFoundError: django` | `.venv` não ativado | `source .venv/bin/activate` |
