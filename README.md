# ProvaPay — Controle de Pagamentos RPA de Aplicadores (Colégio Bernoulli)

> Repositório do TP1 de Engenharia de Software (tp1-eng-soft)

## Integrantes

- Ana Clara dos Anjos Patrício de Novais - frontend
- Bernardo Pedroso Magalhães - back
- Bernardo Zschaber Morato Nogueira - full
- Lucas Ferreira Marinho - full

## Objetivo do sistema (~5 linhas):

O ProvaPay automatiza o controle de pagamentos via RPA (Recibo de Pagamento Autônomo) dos aplicadores de prova que prestam serviço freelancer para o Colégio Bernoulli. Hoje esse processo é feito manualmente em planilhas Excel separadas, uma de cadastro/agendamento dos aplicadores e outra de conferência de lançamentos, valores e unidades, o que é sujeito a erro e difícil de auditar. O sistema unifica esses dados em um banco único e em uma interface web interativa, permitindo importar ou lançar as atividades realizadas por aplicador, evento, data e unidade do colégio. A partir do valor líquido recebido em cada atividade, o sistema calcula automaticamente o valor bruto do RPA e os descontos de INSS, ISS e IR, além de consolidar o total a pagar por aplicador. O objetivo é dar mais confiabilidade, rastreabilidade e agilidade ao fechamento mensal de pagamentos, substituindo o fluxo atual baseado em planilhas.

## Tecnologias (linguagem, frameworks, BD e agentes de IA):

- Linguagem: Python
- Frameworks: Django (backend + API REST, com Django REST Framework) e Django Templates/HTML, CSS e JavaScript (frontend web)
- BD: PostgreSQL
- Agentes de IA: Claude Code (Opus 5), OpenAI Codex (GPT-5.6), Google Gemini (3.1 Pro)

## Histórias de usuários (~8 histórias com 1-2 linhas por história):

- História 1: Como administrador financeiro, quero cadastrar e manter os dados dos aplicadores (dados pessoais, bancários, curso e instituição) em um banco de dados único, para não depender mais de planilhas de agendamento espalhadas por unidade.
- História 2: Como usuário do RH, quero importar listas de aplicação (arquivos .xlsx/.xlsm) com o nome do evento, a data e o valor líquido recebido por aplicador, para lançar rapidamente os serviços prestados em cada prova.
- História 3: Como usuário do RH, quero também lançar manualmente um serviço prestado (aplicador, evento, data e valor), para cobrir os casos que não vêm de uma planilha de agendamento.
- História 4: Como usuário do RH, quero que o sistema calcule automaticamente o valor bruto do RPA e os descontos de INSS (11%), ISS (5%) e IR a partir do valor líquido informado, para eliminar cálculos manuais sujeitos a erro.
- História 5: Como gestor financeiro, quero visualizar um resumo consolidado de pagamento por aplicador (valor bruto, descontos e valor final), para conferir quanto cada aplicador vai receber no fechamento do mês.
- História 6: Como gestor financeiro, quero filtrar e consolidar os lançamentos por unidade do colégio (ex.: Lourdes, Cidade Jardim, Santo Antônio, Vale do Sereno) e empresa pagadora, para organizar o pagamento conforme a estrutura administrativa.
- História 7: Como usuário do RH, quero que o sistema sinalize automaticamente inconsistências entre o valor lançado e o valor recalculado, para reproduzir a conferência que hoje é feita manualmente na planilha de controle.
- História 8: Como gestor financeiro, quero exportar os lançamentos e o resumo por aplicador em uma planilha Excel, para enviar o arquivo final ao setor de contabilidade/pagamento.


