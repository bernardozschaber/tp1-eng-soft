# Como contribuir

## Fluxo

1. **Uma branch por história ou correção**, a partir da `main` atualizada:
   `feat/importacao-formulario`, `fix/titulo-quinzena`.
2. **Pull request para a `main`**, com pelo menos **um revisor** que não seja
   o autor. Ninguém faz push direto na `main`.
3. **O CI tem de passar** antes do merge: ruff, `node --check` e a suíte.
4. **Squash ou rebase no merge**, para a `main` ter um commit por mudança.

## Commits

- [Conventional Commits](https://www.conventionalcommits.org/pt-br/):
  `feat`, `fix`, `test`, `docs`, `refactor`, `style`, `build`, `ci`, `chore`.
- **Um commit é uma mudança lógica, não um arquivo.** Cada commit precisa
  deixar o sistema rodando e os testes verdes, senão `git bisect` e
  `git revert` deixam de funcionar.
- **Mire em até ~100 linhas**, mas o limite serve para separar mudanças,
  não para cortar uma mudança ao meio. Uma função não vai em `(1/11)`: se
  ela é grande, divida pelo que ela faz (o cálculo num commit, a tela em
  outro), com cada parte funcionando.
- **A mensagem diz o quê e por quê.** "update summary template" não diz
  nada; "fix(payroll): return the fortnight label used as export block
  title" diz. Não repita a mesma mensagem em commits diferentes.
- **Commite com a sua identidade.** Confira `git config user.name` e
  `user.email` antes do primeiro commit; o `.mailmap` só corrige o passado.

## Pronto

Uma história só está pronta quando:

- tem teste para a regra de negócio que ela introduz ou muda;
- a tela foi aberta no navegador e o fluxo foi percorrido;
- a documentação afetada (`README.md`, `TESTES.md`) foi atualizada no
  **mesmo PR**.

## Rodando localmente

```bash
pip install -r requirements-dev.txt
ruff check .
python manage.py test
```
