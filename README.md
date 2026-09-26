# ProvaPay — Controle de Pagamentos RPA de Aplicadores (Colégio Bernoulli)

> Repositório do TP1 de Engenharia de Software (tp1-eng-soft)

## Integrantes

* Ana Clara dos Anjos Patrício de Novais - frontend
* Bernardo Pedroso Magalhães - back
* Bernardo Zschaber Morato Nogueira - full
* Lucas Ferreira Marinho - full

## Objetivo do sistema (\~5 linhas):

O ProvaPay automatiza o controle de pagamentos via RPA (Recibo de Pagamento Autônomo) dos aplicadores de prova que prestam serviço freelancer para o Colégio Bernoulli. Hoje esse processo é feito manualmente em planilhas Excel separadas — uma de cadastro/agendamento dos aplicadores e outra de conferência de lançamentos, valores e unidades — o que é sujeito a erro e difícil de auditar. O sistema unifica esses dados em um banco único e em uma interface web interativa, permitindo importar ou lançar as atividades realizadas por aplicador, evento, data e unidade do colégio. A partir do valor líquido recebido em cada atividade, o sistema calcula automaticamente o valor bruto do RPA e os descontos de INSS, ISS e IR, além de consolidar o total a pagar por aplicador. O objetivo é dar mais confiabilidade, rastreabilidade e agilidade ao fechamento mensal de pagamentos, substituindo o fluxo atual baseado em planilhas.

## Tecnologias (linguagem, frameworks, BD e agentes de IA):

* Linguagem: Python 3.13
* Frameworks: Django 5.2 (backend + API REST com Django REST Framework) e Django Templates + CSS e JavaScript puros (frontend web)
* Leitura/escrita de planilhas: openpyxl
* BD: PostgreSQL (via `DATABASE\\\_URL`); SQLite como fallback para desenvolvimento local
* Agentes de IA: Claude Code (Fable 5.1), OpenAI Codex (GPT-5.6), Google Gemini (3.1 Pro)

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
python3 -m venv .venv \\\&\\\& source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed --demo        # cadastros padrão, usuário admin/admin e dados fictícios
python manage.py runserver
```

Acesse http://127.0.0.1:8000 e entre com `admin` / `admin`.

Para usar PostgreSQL, suba o banco com `docker compose up -d` e exporte
`DATABASE\\\_URL=postgres://provapay:provapay@localhost:5432/provapay` antes de rodar
`migrate` (ver `.env.example`). Sem a variável o projeto usa `db.sqlite3`.

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
|Importação|lê todas as abas no layout "Relatório de Atividade"; cria aplicadores desconhecidos marcados como *cadastro incompleto*; sinaliza possíveis duplicatas|

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
docs/samples/      lista de pagamento de exemplo com nomes fictícios
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

