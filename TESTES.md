# Testes, medições e correções

Este documento registra o que foi **apurado, medido e corrigido** no BernoulliPay,
com os números que sustentam cada decisão. Nada aqui é estimativa: toda afirmação
de desempenho vem de uma execução reproduzível, e toda afirmação de acessibilidade
vem de um cálculo ou de uma ferramenta, não de impressão visual.

Três frentes: **desempenho em escala real**, **qualidade de interface** e
**integridade dos valores pagos**. A terceira trouxe junto a primeira suíte de
testes automatizados do projeto, descrita na seção 4 — é dela que o TP2 parte.

---

## 1. Desempenho em escala real

### 1.1 Por que isso foi investigado

O banco de desenvolvimento tinha 217 lançamentos. O volume real de operação é de
cerca de **1.000 lançamentos por semana** — ~52.000/ano, ~520.000 em dez anos.
Uma primeira análise feita sobre os dados de demonstração concluiu, erradamente,
que SQLite bastaria. Ao medir no volume correto, a conclusão mudou, e mais
importante: o gargalo real **não era o banco de dados**.

### 1.2 Metodologia

- Banco descartável em SQLite, populado com `bulk_create`
- 52.014 lançamentos (um ano), 400 aplicadores, 4 unidades, 6 setores,
  datas de pagamento derivadas pela regra de negócio real (dia 5 / dia 20)
- Medição via `django.test.Client` com `DEBUG=True` para contar queries
- Memória via `tracemalloc` (pico da requisição)
- O banco de produção (`db.sqlite3`) **não foi tocado** em nenhum momento

### 1.3 O que foi encontrado — ANTES

| Página | Tempo | Queries | Pico de RAM |
|---|---:|---:|---:|
| Dashboard | 0,21s | 16 | — |
| Lançamentos (paginado) | 0,09s | 9 | — |
| **Resumo** (sem filtro) | **35,78s** | 7 | **189 MB** |
| **Export Excel** (sem filtro) | **164,04s** | 4 | **534 MB** |

**A coluna de queries é a descoberta.** Sete e quatro consultas. Não há N+1 —
`filters.py` já usava `select_related("applicator", "unit", "sector", "paying_company")`.
As consultas isoladas são rápidas: 0,04s para a lista paginada e **0,01s** para
filtrar por `payment_date` retornando 2.156 linhas.

Portanto os 35s e os 164s são **inteiramente** agregação em Python, renderização de
template e construção do workbook pelo openpyxl. Trocar o banco não moveria nenhum
dos dois números.

Diagnóstico preciso:

- **Resumo**: montava **28.936 linhas** de tabela num único HTML, sem paginação.
- **Export**: 534 MB de pico numa requisição. Em uma VPS com poucos workers isso é
  *OOM kill*; 164s estoura o timeout padrão de gunicorn/nginx (30–60s), então o
  usuário receberia 502 em vez de um arquivo.
- Além disso, o export avaliava o queryset **duas vezes** (`build_summary` reordenava
  internamente, disparando uma segunda busca das mesmas linhas).
- **Índices ausentes**: as chaves estrangeiras receberam índice automático do Django,
  mas `activity_date` e `payment_date` — que governam a ordenação padrão, os filtros
  de data e o agrupamento do resumo — não tinham nenhum.

### 1.4 O que foi corrigido

1. **Escopo obrigatório por ciclo de pagamento** (`EntryFilters.scope_to_payment_run()`).
   O Resumo e o Export são documentos de um fechamento: a operação paga uma coorte
   por vez. Sem data na requisição, usa-se a mais recente, e a página informa isso
   explicitamente. *Não existe* a opção de exportar o histórico inteiro — era a
   funcionalidade que quebrava a aplicação.
2. **Uma única materialização no export** (`build_summary_from()`), eliminando a
   segunda busca das mesmas linhas.
3. **Índices**: `db_index` em `activity_date` e `payment_date`, mais um índice
   composto `(payment_date, applicator)` que serve ao agrupamento e à ordenação do
   resumo sem passo de sort. Migração `payroll/0002`.

### 1.5 Resultado — DEPOIS

Medido contra a **maior coorte realista** (2.375 lançamentos), não contra a mais
recente — que na amostra tinha apenas 11 e daria um número lisonjeiro e falso.

| Página | Antes | Depois | Ganho |
|---|---:|---:|---:|
| Resumo | 35,78s / 189 MB | **2,41s / 23 MB** | 15× mais rápido, 8× menos memória |
| Export | 164,04s / 534 MB | **6,44s / 24 MB** | 25× mais rápido, 22× menos memória |

### 1.6 A prova que mais importa: o custo deixou de crescer com o histórico

O histórico foi **quadruplicado** — de 52.014 para 208.014 lançamentos, ~4 anos —
mantendo a mesma coorte de teste intacta:

| Página (coorte de 2.375) | 52 mil de histórico | 208 mil de histórico |
|---|---:|---:|
| Resumo | 2,27s / 23,0 MB | 2,41s / 23,0 MB |
| Export | 6,57s / 24,2 MB | 6,44s / 24,2 MB |

Quadruplicar o histórico **não mudou nada**; a memória ficou idêntica. O custo passou
a ser limitado pelo tamanho de um ciclo de pagamento, não pelo volume acumulado. Em
dez anos a coorte continua com ~2.000 lançamentos e esses números se mantêm.

### 1.7 Decisão sobre o banco

**PostgreSQL**, com SQLite como fallback local (`DATABASE_URL` ausente). A escolha
não se justifica por desempenho de consulta — o benchmark acima mostra que, nesse
volume, as consultas não são o problema. Justifica-se por **durabilidade**: backup,
recuperação *point-in-time* e concorrência real de escrita durante o fechamento,
num sistema que deve durar anos. O nome do banco, usuário e volume foram alinhados
à marca (`bernoullipay`).

### 1.8 Como reproduzir

```bash
# banco descartável, sem tocar no db.sqlite3
export BENCH=/tmp/bench.sqlite3 && rm -f $BENCH
DATABASE_URL="sqlite:///$BENCH" python manage.py migrate
DATABASE_URL="sqlite:///$BENCH" python manage.py seed
# popular com bulk_create e medir com django.test.Client + tracemalloc
```

### 1.9 O que continua em aberto

- 6,44s no export é aceitável para um download deliberado, mas continua sendo
  trabalho síncrono. Se o volume por ciclo crescer muito além de ~2.500 lançamentos,
  o caminho é `openpyxl` em modo `write_only` ou geração assíncrona. Não foi feito
  agora porque `export.py` reproduz a formatação da planilha legada célula a célula,
  e o modo `write_only` restringe merges e alturas de linha — o risco de quebrar a
  compatibilidade com a rotina existente não se paga no volume atual.
- As medições desta seção são scripts executados sob demanda, não testes de
  regressão: nada quebra automaticamente se o resumo voltar a percorrer o
  histórico inteiro. A suíte que existe hoje (seção 4) cobre corretude de
  pagamento, não desempenho. Transformar o teto de queries desta seção em
  asserção (`assertNumQueries`) é o primeiro item do roteiro em 4.4.

---

## 2. Qualidade de interface

Apurado com o **Impeccable** (`/impeccable audit`, `critique`, `typeset`), com o
detector mecânico da ferramenta e com cálculos próprios de contraste WCAG.

### 2.1 Nota inicial: 12/20 — "Acceptable, significant work needed"

| Dimensão | Nota | Achado principal |
|---|---:|---|
| Acessibilidade | 2/4 | Indicador de foco em 1,19:1 |
| Desempenho | 3/4 | Enxuto; `transition: width` morta |
| Responsividade | 2/4 | Botão de barra lateral morto abaixo de 1024px |
| Tematização | 3/4 | Sem `color-scheme`; hex fora do sistema de tokens |
| Integridade | 2/4 | Sistema visual portado de outro produto |

### 2.2 Contraste — seis pares reprovavam em AA

Calculado, não estimado (fórmula de luminância relativa da WCAG 2.1):

| Par | Antes | Depois |
|---|---:|---:|
| `--text-subdued` sobre branco | 2,68 | **4,74** |
| `--text-success` sobre branco | 3,09 | **5,41** |
| `--text-secondary` sobre cinza inset | 4,43 | **6,24** |
| `badge--brand` sobre tinta de marca | 4,08 | **5,13** |
| `badge--gray` sobre cinza 100 | 4,16 | **5,87** |
| `--text-destructive` sobre branco | 4,36 | **5,86** |

Verificação final: **17 de 17 pares aprovados**, incluindo os limites de 3:1 para
elementos não textuais.

### 2.3 Acessibilidade — corrigido

- **Foco**: `outline: 0` em todo input dentro de `.field`, substituído por um anel de
  `rgba(11,11,11,0.08)` — **1,19:1**, onde o critério 1.4.11 exige 3:1. Agora é um
  contorno de 2px em `--focus-ring`: **12,08:1**.
- **Checkboxes do preview de importação** sem nome acessível — o controle que decide
  *quem recebe pagamento*. Um leitor de tela anunciava "checkbox, marcado", sem dizer
  qual aplicador. Passaram a ter `aria-label` com o nome.
- **Estrutura de cabeçalhos**: toda página tinha exatamente um heading. Títulos de
  card viraram `<h2>` (16 renderizados), sem diferença visual.
- **120 atributos `scope="col"`**; três colunas em branco ganharam rótulos `.sr-only`.
- **Gráfico** sem alternativa textual: ganhou `role="img"` e descrição gerada pelo
  servidor com o total e a contagem reais do período.
- **`color-scheme: light`**: sem isso, seletores de data e checkboxes nativos
  renderizavam escuros em SO no modo escuro.
- **Setas `↑`/`↓`** em Unicode substituídas por ícones Lucide desenhados, coerentes
  com o resto do sistema de ícones.

### 2.4 Responsividade

Abaixo de 1024px a barra lateral tinha `display: none` incondicional, enquanto o
botão de alternância continuava visível em todas as páginas — um controle rotulado
que não fazia nada, e os totais por unidade (que não existem em nenhum outro lugar)
ficavam inalcançáveis. Virou gaveta sobreposta com backdrop, fechamento por `Escape`,
devolução de foco e `aria-expanded`. Alvos de toque subiram para 40px.

### 2.5 Segurança

`upload.js` interpolava `file.name` direto em `innerHTML`. Um arquivo chamado
`<img src=x onerror=...>.xlsx` executava ao ser selecionado. É *self-XSS* — a pessoa
precisa escolher o próprio arquivo hostil — mas é uma falha de injeção num sistema de
folha de pagamento. Passou a usar `createElement` + `textContent`.

### 2.6 Identidade visual

> A **criação** da identidade — as duas rodadas de geração, as ferramentas usadas
> (**v0.app** na primeira, **geração de imagens do ChatGPT** na segunda), a restrição
> explícita de não parecer com o PicPay, os dez conceitos de cada rodada e o refinamento
> do escolhido — está em [`DESIGN.md`](DESIGN.md), seção `## Identity`.
> Esta seção registra apenas o que foi **medido** sobre o resultado.

O sistema visual era uma **porta declarada** do design system do Maybe (aplicativo de
finanças pessoais), com os comentários dizendo isso nos próprios arquivos, incluindo
`"Stat block (net worth style)"` e `"Weight bar (asset allocation style)"`.

Substituído pelo **verde Bernoulli `#009E8E`**. A restrição que governa todo o uso:
`#009E8E` tem **3,34:1 sobre branco** — passa no piso de 3:1 para elementos gráficos
e reprova no de 4,5:1 para texto. É cor de preenchimento, traço e marca, nunca texto
em superfície clara; texto de marca usa `#047569` (5,59:1). Essa regra está escrita
dentro do `tokens.css`.

Por isso o botão primário **não** virou verde: branco sobre `#009E8E` reprovaria em
contraste de texto de botão.

### 2.7 Paleta categórica — validada, não escolhida a olho

A paleta das unidades vinha do Maybe. Submetida ao validador de paletas do skill
`dataviz`, **reprovou em três dos cinco critérios**:

| Critério | Resultado |
|---|---|
| Piso de croma | `#737373` com croma 0,000 — lê como cinza, não como categoria |
| Separação CVD | violeta/azul com ΔE 4,9 (deuteranopia) |
| Piso de visão normal | violeta/azul com ΔE 14,4 — abaixo do corte de 15 |

Esse último significa que pessoas **com visão de cores normal** não distinguiam duas
unidades com segurança.

A substituição não foi escolhida a olho: é uma busca de ponto mais distante em OKLCH,
restrita a uma faixa de croma contida (0,10–0,16) para não destoar de um console
administrativo quase acromático. Uma busca sem restrição devolvia `#0237e5` e
`#00ad00` — maximamente separáveis e completamente errados para o produto.

Resultado: **os cinco critérios aprovados** na lista de pares adjacentes (a regra
correta para a barra empilhada que a paleta pinta), e as quatro primeiras posições —
as quatro unidades reais — também passam no critério mais rígido de todos os pares,
com ΔE mínimo de 16,0.

### 2.8 Tipografia

- **36 literais em `px` → 9 papéis em `rem`**. A escala inteira estava em px, o que
  ignorava silenciosamente a preferência de tamanho de fonte do navegador.
- **O total a pagar** subiu para 36px e ganhou algarismos tabulares. Empatava em 30px
  com o `<h1>` (que no painel é uma saudação) e era a única cifra do sistema sem
  `tabular-nums`.
- **Medida de leitura** de 68ch. Não havia `max-width` em lugar nenhum do CSS; a
  página de Ajuda esticava por toda a largura do monitor.
- **Geist → IBM Plex Sans + IBM Plex Mono** (OFL, self-hosted). A troca foi medida
  antes de ser feita: Plex Sans é 3–5% **mais estreita** (tabelas ganharam folga em
  vez de estourar), Plex Mono tem largura de avanço **idêntica** à Geist Mono (as
  colunas de dinheiro não moveram um pixel), diferença de altura-x de 2,6% (abaixo do
  limiar que justificaria recortar a escala) e caixa de linha idêntica em 1,300em.
  Cobertura de `ãáàâçéêíóôõúü` e de `R$ · — ↑ ↓ %` verificada com `fontTools`.

### 2.9 Estado final

- Detector mecânico: **apenas 2 avisos**, ambos de raio de borda pré-existentes
  (`4px` no indicador de navegação, `1px` nos ticks), mantidos deliberadamente fora
  da escala documentada para não serem herdados por superfícies futuras.
- Detector de tipografia: **zero achados**.
- Contraste: **17/17 aprovados**.
- Todas as 10 rotas retornam 200.

### 2.10 O que NÃO foi verificado

Declarado explicitamente para que ninguém confie mais do que deve:

- **Nenhum JavaScript foi executado.** Não há runtime JS na máquina de
  desenvolvimento usada (sem node/deno/bun). As mudanças em `app.js`, `chart.js`,
  `upload.js` e `preview.js` foram revisadas e têm parênteses/chaves balanceados,
  mas **não foram executadas**.
- **Nenhuma página foi renderizada em navegador.** Não havia driver de automação
  disponível. Os achados de responsividade e de alvo de toque vêm de análise estática
  do CSS, não de viewport renderizado nem de gesto de toque sintetizado.
- **O `docker compose up -d` não foi executado** — não há daemon Docker na máquina.
  A configuração do Postgres foi validada por parsing de `DATABASE_URL` e por
  comparação estrutural com a versão anterior, não por execução.

Recomendação: abrir a aplicação e percorrer o fluxo de importação, a gaveta lateral
e o export antes da apresentação.

---

## 3. Integridade dos valores pagos: o mesmo serviço lançado duas vezes

### 3.1 Como o defeito apareceu

Na conferência do fechamento de 05/10/2026, oito aplicadores apareciam com o
mesmo serviço repetido — três vezes, em alguns casos:

```
Joao Dario Lodi Campolina
Orientador  Oficina de Redação  08/09/2026  Lourdes  05/10/2026  R$87,00  R$103,57 …
Orientador  Oficina de Redação  08/09/2026  Lourdes  05/10/2026  R$87,00  R$103,57 …
Orientador  Oficina de Redação  08/09/2026  Lourdes  05/10/2026  R$87,00  R$103,57 …
```

Nada na tela dizia que aquilo era erro. O resumo apenas somava um total maior.

### 3.2 A causa, medida nos arquivos

A hipótese natural — falha de leitura da planilha — estava errada. As oito
repetições vieram de **lotes de importação diferentes**: os mesmos serviços
chegaram em três workbooks distintos.

A operação monta a lista da semana copiando a da semana anterior, e as abas que
não mudam ficam com a data antiga:

| Arquivo | Aba `Reapl manhã` | Aba `OFICINA MANHÃ` | Aba `OFICINA tarde` |
|---|---|---|---|
| `08-09 Reaplicação e Oficinas.xlsx` | 08 de Setembro | 08 de Setembro | 08 de Setembro |
| `14-09 Reaplicação e Simulados.xlsx` | 14 de Setembro | **08 de Setembro** | **08 de Setembro** |
| `15-09 Reaplicação e Simulados.xlsx` | 15 de Setembro | 15 de Setembro | **08 de Setembro** |

Os três arquivos têm a mesma lista de abas — são cópias uns dos outros. O parser
leu exatamente o que estava escrito; o erro chegou correto do arquivo.

### 3.3 O que estava errado no sistema

A pré-visualização **já marcava** a linha como duplicada (`row["is_duplicate"]`),
mas `confirm_import` gravava assim mesmo. O aviso era decorativo. Pior: a
comparação incluía o valor líquido, de modo que a mesma oficina relançada com
valor corrigido nem sequer era marcada.

Havia três caminhos de gravação e **nenhum** deles verificava o que quer que
fosse antes de inserir: a importação, o formulário manual e qualquer escrita
direta pelo ORM.

### 3.4 O que define "o mesmo serviço"

A questão não é trivial, e errá-la custa nos dois sentidos: uma chave larga
demais deixa passar a duplicata, uma chave estreita demais **apaga pagamento
devido**.

A planilha de controle de referência (`2026 - BH - LD - Planilha de controle e
conferência de RPAS…`) foi usada como evidência. Ela tem 885 linhas de serviço,
e em **35 pares** a mesma pessoa aparece com a mesma data, a mesma atividade e a
mesma função. Em 21 desses pares os valores são diferentes:

```
Maria Wolff Florencio  93  APLICADOR  2026-05-05  Oficina de Redação  LOURDES
Maria Wolff Florencio  84  APLICADOR  2026-05-05  Oficina de Redação  LOURDES
```

Não é duplicata: é a oficina da **manhã** e a da **tarde**, com valores
diferentes porque os turnos pagam diferente. A planilha legada não tem coluna de
turno, então ela não consegue distinguir os dois casos — foi por isso que o
problema sobreviveu tantos anos no processo manual.

Daí a chave adotada, que inclui o turno:

> **aplicador · data da atividade · atividade · turno · função · unidade**

O valor líquido **não** entra: a mesma oficina relançada com valor corrigido
continua sendo a mesma oficina, e é exatamente o caso que a versão anterior
deixava passar.

A atividade entra na forma canônica (`event_key`: maiúsculas, sem acento, espaço
simples), porque `"Oficina de Redação"`, `"OFICINA DE REDACAO"` e
`"Oficina de Redação "` são a mesma coisa para quem paga.