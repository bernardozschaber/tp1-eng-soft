# BernoulliPay — Controle de Pagamentos RPA de Aplicadores (Colégio Bernoulli)

> Repositório do TP1 de Engenharia de Software (tp1-eng-soft)

## Integrantes

* Ana Clara dos Anjos Patrício de Novais - frontend
* Bernardo Pedroso Magalhães - back
* Bernardo Zschaber Morato Nogueira - full
* Lucas Ferreira Marinho - full

## Objetivo do sistema (\~5 linhas):

O BernoulliPay automatiza o controle de pagamentos via RPA (Recibo de Pagamento Autônomo) dos aplicadores de prova que prestam serviço freelancer para o Colégio Bernoulli. Hoje esse processo é feito manualmente em planilhas Excel separadas — uma de cadastro/agendamento dos aplicadores e outra de conferência de lançamentos, valores e unidades — o que é sujeito a erro e difícil de auditar. O sistema unifica esses dados em um banco único e em uma interface web interativa, permitindo importar ou lançar as atividades realizadas por aplicador, evento, data e unidade do colégio. A partir do valor líquido recebido em cada atividade, o sistema calcula automaticamente o valor bruto do RPA e os descontos de INSS, ISS e IR, além de consolidar o total a pagar por aplicador. O objetivo é dar mais confiabilidade, rastreabilidade e agilidade ao fechamento mensal de pagamentos, substituindo o fluxo atual baseado em planilhas.

## Tecnologias (linguagem, frameworks, BD e agentes de IA):

* Linguagem: Python 3.13
* Frameworks: Django 5.2 (backend + API REST com Django REST Framework) e Django Templates + CSS e JavaScript puros (frontend web)
* Leitura/escrita de planilhas: openpyxl
* BD: PostgreSQL (via `DATABASE\\\_URL`); SQLite como fallback para desenvolvimento local
* Agentes de IA (código): Claude Code (Fable 5.1), OpenAI Codex (GPT-5.6), Google Gemini (3.1 Pro)
* IA generativa (identidade visual): **v0.app** — primeira rodada de conceitos de logo e a galeria
  de comparação; **geração de imagens do ChatGPT** — segunda rodada e os arquivos finais. O processo
  completo, com os briefings e o que foi descartado, está em [`DESIGN.md`](DESIGN.md), seção
  `## Identity`.

## Histórias de usuários (\~8 histórias com 1-2 linhas por história):

* História 1: Como administrador financeiro, quero cadastrar e manter os dados dos aplicadores (dados pessoais, bancários, curso e instituição) em um banco de dados único, para não depender mais de planilhas de agendamento espalhadas por unidade.
* História 2: Como usuário do RH, quero importar listas de aplicação (arquivos .xlsx/.xlsm) com o nome do evento, a data e o valor líquido recebido por aplicador, para lançar rapidamente os serviços prestados em cada prova.
* História 3: Como usuário do RH, quero também lançar manualmente um serviço prestado (aplicador, evento, data e valor), para cobrir os casos que não vêm de uma planilha de agendamento.
* História 4: Como usuário do RH, quero que o sistema calcule automaticamente o valor bruto do RPA e os descontos de INSS (11%), ISS (5%) e IR a partir do valor líquido informado, para eliminar cálculos manuais sujeitos a erro.
* História 5: Como gestor financeiro, quero visualizar um resumo consolidado de pagamento por aplicador (valor bruto, descontos e valor final), para conferir quanto cada aplicador vai receber no fechamento do mês.
* História 6: Como gestor financeiro, quero filtrar e consolidar os lançamentos por unidade do colégio (ex.: Lourdes, Cidade Jardim, Santo Antônio, Vale do Sereno) e empresa pagadora, para organizar o pagamento conforme a estrutura administrativa.
* História 7: Como usuário do RH, quero que o sistema sinalize automaticamente inconsistências entre o valor lançado e o valor recalculado, para reproduzir a conferência que hoje é feita manualmente na planilha de controle.
* História 8: Como gestor financeiro, quero exportar os lançamentos e o resumo por aplicador em uma planilha Excel, para enviar o arquivo final ao setor de contabilidade/pagamento.

## Como executar

```bash
python3 -m venv .venv \\\&\\\& source .venv/bin/activate ## para criar a variável de ambiente do banco // para ativar o banco
pip install -r requirements.txt
python manage.py migrate
python manage.py seed               # dados de referência (unidades, setores, alíquotas) e usuário admin/admin
python manage.py seed_team          # equipe de aplicação de provas, com foto, cargo e contato
python manage.py runserver
```

Acesse http://127.0.0.1:8000 e entre com `admin` / `admin`.

### Subindo o live server com o `.venv` já criado

Sequência exata usada para colocar o servidor de desenvolvimento no ar quando o
ambiente virtual já existe (chamando o Python do `.venv` direto, sem `activate`):

```bash
cd /home/brnrdzschbr/Debian/prova-pay
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py check
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

O `0.0.0.0` faz o servidor responder também pelo IP da máquina, o que é útil no
WSL. Para conferir que subiu, de outro terminal:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/        # 302 (redireciona para o login)
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/login/  # 200
```

As planilhas importadas são guardadas em `media/imports/AAAA/MM/` (fora de
`static/`, e servidas só pela view autenticada `imports:batch_download`). O
diretório já está no `.gitignore`; um workbook típico tem algumas dezenas de KB.

### A lista de aplicadores é a fonte da verdade

`/aplicadores` guarda os cadastros conferidos, com nome completo, CPF,
WhatsApp, e-mail e situação. A situação tem dois valores:

* **cadastro novo: primeiro pagamento** — todo cadastro nasce assim, seja
  criado à mão ou confirmado numa importação;
* **cadastro ativo: pagamento recorrente** — a pessoa aparece numa segunda
  data de pagamento (ou veio da lista conferida, que é histórico de quem já
  recebeu). A promoção é automática, no momento em que o lançamento é salvo,
  e não volta atrás.

A coluna **Ficha** abre o cartão da pessoa; o **WhatsApp** é um ícone que leva
direto à conversa, montado a partir do celular da ficha (quando há dois
números, o fixo é descartado). A ficha tem o botão de excluir o cadastro, que
recusa quem já tem lançamento — nesse caso o caminho é marcar como inativo.

A lista conferida entra pelo comando `roster`, que lê as duas planilhas do
setor:

```bash
python manage.py roster \
  --payments "2026 - BH - LD - Planilha de controle e conferência de RPAS - Aplicadores.xlsm" \
  --profiles "10 - Planilha - Agendamento aplicadores - Outubro (Lourdes).xlsm" \
  --replace                                   # --replace apaga os cadastros atuais

python manage.py roster nomes.txt             # ou uma lista simples, um nome por linha
```

Cada planilha tem um papel:

* `--payments`, aba **RESUMO DE PGTO POR APLICADOR**, coluna **APLICADOR**: diz
  **quem** entra no cadastro — quem já recebeu em alguma quinzena;
* `--profiles`, aba **Aplicadores**: diz **o que se sabe** de cada pessoa
  (identidade, nascimento, bairro, curso, banco, PIX, PIS/NIT, indicação) e só
  completa quem a primeira trouxe; não cria ninguém.

O casamento entre as duas é por nome, com uma regra apertada
(`applicators/names.py:is_same_person`): o nome curto tem que caber inteiro no
longo, palavra por palavra e na ordem, tolerando abreviação
(“B. Luisa S. M. de Assis”) e uma letra trocada (“Linfgren”/“Lindgren”). Nome
que casa com duas fichas não recebe nenhuma e sai no relatório do comando.
Quando duas grafias casam com a mesma ficha, elas viram um cadastro só, com o
nome da ficha.

A ficha completa fica em `/aplicadores/<id>/ficha/` — um cartão no meio da
tela, com espaço para a foto 3x4 — e abre ao clicar no nome na lista. A lista
continua mostrando só nome, CPF, WhatsApp, e-mail e situação.

Na importação, cada nome da planilha é comparado com essa lista. Nome igual
cai no cadastro existente; nome parecido (“Carolina Mattos” ao lado de
“Carolina Mattos Lindgren Alves”) vira a pergunta “é a mesma pessoa?”; nome que
não se parece com ninguém vira a pergunta “criar um novo cadastro para o
usuário a seguir: X?”. Só o “sim” dessa última cria o cadastro, marcado como
primeiro pagamento; o “não” deixa as linhas daquele nome de fora do lote.

`seed_team` cria os logins da equipe. A senha de cada pessoa é o PIN de quatro
dígitos no fim do próprio telefone:

| Login | Pessoa | Cargo | PIN |
|---|---|---|---|
| `jessica.moreira` | Jessica Souza Moreira | ♾️ Supervisor - Aplicação de Prova | `2433` |
| `fernanda` | Fernanda | Aplicação de Provas (Vale do Sereno) | `1387` |
| `felipe` | Felipe | Aplicação de Provas (Lourdes) | `5424` |
| `ana.julia` | Ana Júlia | Aplicação de Provas (Cidade Jardim) | `0089` |
| `suzana.godoy` | Suzana Godoy | Coordenadora de Operações | `3608` |

Para usar PostgreSQL, suba o banco com `docker compose up -d` e exporte
`DATABASE\\\_URL=postgres://bernoullipay:bernoullipay@localhost:5432/bernoullipay` antes de rodar
`migrate` (ver `.env.example`). Sem a variável o projeto usa `db.sqlite3`.

> **Vindo de uma versão anterior?** O banco, o usuário e o volume do Postgres foram
> renomeados de `provapay` para `bernoullipay` junto com o rebranding. O Postgres só cria
> o usuário e o banco quando o diretório de dados está vazio, então o volume também mudou
> de nome (`bernoullipay_pgdata`) — assim um `docker compose up -d` já sobe limpo, sem erro
> de autenticação. O volume antigo não é apagado, apenas fica órfão: remova com
> `docker volume rm pgdata` quando tiver certeza de que não precisa mais dele.

## Testes e medições

As decisões de desempenho e de interface deste projeto estão documentadas em
[`TESTES.md`](TESTES.md), com os números que as sustentam: benchmarks em volume real
(52 mil e 208 mil lançamentos), razões de contraste WCAG calculadas, validação da
paleta categórica e o que explicitamente **não** foi verificado.

Destaques: o Resumo saiu de 35,8s/189 MB para 2,4s/23 MB e o export de 164,0s/534 MB
para 6,4s/24 MB, e o custo de ambos deixou de crescer com o histórico acumulado.

## Regras de negócio

|Regra|Implementação|
|-|-|
|Bruto do RPA a partir do líquido|`bruto = líquido ÷ (1 − INSS − ISS − IR)`; com 11% + 5% + 0% o divisor é 0,84 (`apps/payroll/calculator.py`)|
|Descontos|`INSS = bruto × 11%`, `ISS = bruto × 5%`, `IR = bruto × IR%`; alíquotas editáveis em Configurações (`TaxSettings`)|
|Ajuste de −R$0,01 da planilha antiga|**Não aplicado**, por decisão do setor|
|Data de pagamento|atividade até o dia 15 → dia 5 do mês seguinte; após o dia 15 → dia 20 do mês seguinte (`apps/payroll/schedule.py`)|
|Empresa pagadora|derivada da unidade (Lourdes → RRPM Matriz, Cidade Jardim → RRPM CJ, Santo Antônio → RRPM GO, Vale do Sereno → RRPM VSE)|
|Consistência|`|
|Resumo por aplicador|agrupa por (data de pagamento, aplicador, empresa pagadora), como a aba RESUMO DE PGTO POR APLICADOR|
|Importação|dois formatos: **"Relatório de Atividade"** (Lourdes), com o valor na planilha; e **exportação de formulário** (Cidade Jardim e Vale do Sereno), com nome completo, CPF e função por resposta — nesse caso a prova, o dia e o turno saem do nome do arquivo ("Prova Regular 11-09 Tarde.xlsx") e o valor por pessoa é informado na pré-visualização. Casa o aplicador por CPF e, na falta dele, por nome; cria desconhecidos marcados como *cadastro incompleto*; sinaliza possíveis duplicatas|

## Arquitetura

Monólito Django em camadas. Cada app tem responsabilidade única e as regras de
negócio ficam em módulos puros (sem dependência de request/response), o que permite
reutilizá-las nas páginas HTML, na API REST e no comando de seed.

```
config/            settings, urls, wsgi
apps/
  core/            layout base, dashboard, login, template tags (ícones, moeda)
  catalog/         unidades, empresas pagadoras, setores, alíquotas (+ comando seed)
  applicators/     cadastro de aplicadores e normalização de nomes
  payroll/         lançamentos, calculadora RPA, calendário de pagamento, resumo, exportação
  imports/         parser das listas de pagamento e fluxo upload → prévia → confirmação
  api/             serializers e viewsets DRF (/api/)
templates/         páginas por app
static/            tokens de design (Geist, paleta), CSS de componentes, JS sem frameworks
docs/samples/      lista de pagamento de exemplo, só como referência do parser
```

### Diagrama de classes (domínio)

```mermaid
classDiagram
    class PayingCompany {
        +name
    }
    class Unit {
        +name
        +is\\\_default
    }
    class Sector {
        +name
        +is\\\_default
    }
    class TaxSettings {
        +inss\\\_rate
        +iss\\\_rate
        +ir\\\_rate
        +current()$
    }
    class Applicator {
        +full\\\_name
        +normalized\\\_name
        +cpf
        +bank\\\_account
        +pix\\\_key
        +needs\\\_review
        +find\\\_by\\\_name(raw)$
    }
    class ServiceEntry {
        +role
        +activity\\\_date
        +event\\\_name
        +shift
        +payment\\\_date
        +net\\\_amount
        +gross\\\_amount
        +inss\\\_amount
        +iss\\\_amount
        +ir\\\_amount
        +net\\\_payable
        +is\\\_consistent
        +apply\\\_calculations()
    }
    class ImportBatch {
        +file\\\_name
        +imported\\\_at
    }
    class PayrollCalculator {
        <<module>>
        +compute\\\_breakdown(net, rates) PayrollBreakdown
    }
    class PaymentSchedule {
        <<module>>
        +payment\\\_date\\\_for(activity\\\_date) date
    }

    Unit "\\\*" --> "1" PayingCompany
    ServiceEntry "\\\*" --> "1" Applicator
    ServiceEntry "\\\*" --> "1" Unit
    ServiceEntry "\\\*" --> "1" Sector
    ServiceEntry "\\\*" --> "1" PayingCompany : snapshot
    ServiceEntry "\\\*" --> "0..1" ImportBatch
    ServiceEntry ..> PayrollCalculator : usa
    ServiceEntry ..> PaymentSchedule : usa
    PayrollCalculator ..> TaxSettings : lê alíquotas
```

### Diagrama de sequência (importação de listas)

```mermaid
sequenceDiagram
    actor RH
    participant View as imports.views
    participant Parser as imports.parser
    participant Service as imports.services
    participant DB as Banco de dados

    RH->>View: POST /importar/ (arquivos .xlsx/.xlsm)
    loop para cada arquivo
        View->>Parser: parse\\\_workbook(nome, bytes)
        Parser-->>View: ParsedWorkbook (abas, evento, data, linhas)
    end
    View->>Service: stage\\\_uploads → sessão
    View-->>RH: redirect /importar/previa/
    RH->>View: GET /importar/previa/
    View->>Service: enrich\\\_preview (casa nomes, detecta duplicatas, calcula bruto)
    Service->>DB: Applicator.find\\\_by\\\_name / ServiceEntry.exists
    View-->>RH: blocos por aba (editáveis, com avisos)
    RH->>View: POST /importar/confirmar/ (abas e linhas marcadas)
    View->>Service: confirm\\\_import(payload, sessão, usuário)
    Service->>DB: cria Applicator faltantes (needs\\\_review)
    Service->>DB: cria ImportBatch + ServiceEntry (bruto, INSS, ISS, IR, data pgto)
    Service-->>View: contadores
    View-->>RH: redirect /lancamentos/ com mensagem de sucesso
```

### Diagrama de componentes

```mermaid
flowchart LR
    Browser\\\[Navegador<br/>HTML + CSS + JS] -->|sessão| Views\\\[Views Django<br/>core · payroll · imports · applicators · catalog]
    Browser -->|JSON| API\\\[API REST<br/>Django REST Framework]
    Views --> Domain\\\[Regras de domínio<br/>calculator · schedule · summary · parser · export]
    API --> Domain
    Domain --> ORM\\\[Django ORM]
    ORM --> DB\\\[(PostgreSQL / SQLite)]
    Excel\\\[(Planilhas .xlsx/.xlsm)] -->|openpyxl| Domain
```

## API REST

Autenticação por sessão (faça login na interface e acesse `/api/` no navegador).

|Endpoint|Descrição|
|-|-|
|`GET/POST /api/lancamentos/`|lista/cria lançamentos; filtros `q`, `unit`, `company`, `sector`, `applicator`, `payment\\\_date`, `from`, `to`|
|`GET /api/lancamentos/summary/`|resumo por data de pagamento › aplicador › empresa (mesmos filtros)|
|`GET/POST/PUT/DELETE /api/aplicadores/`|cadastro de aplicadores (`?q=` busca por nome)|
|`GET /api/unidades/`, `/api/setores/`, `/api/empresas/`|tabelas de referência|
|`GET /api/aliquotas/`|alíquotas vigentes|

## Convenções

* Commits seguem [Conventional Commits](https://www.conventionalcommits.org/) e ficam abaixo de \~100 linhas (exceções justificadas na mensagem).
* Código, nomes de variáveis e comentários em inglês; interface em português.
* Interface baseada no design system do [Maybe](https://github.com/maybe-finance/maybe) (fonte Geist, paleta e componentes), reescrito em CSS puro em `static/css/`.
* As planilhas reais do setor não são versionadas (`.gitignore`), pois contêm dados pessoais; use `docs/samples/lista\\\_pagamento\\\_exemplo.xlsx`.