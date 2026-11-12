---
title: Meu currículo, como código
summary: Um registro mestre da minha carreira em Markdown, uma pequena CLI que transforma isso em currículos PDF e Word sob medida, e uma regra rígida de que nada é inventado.
role: Projeto pessoal, 2026
status: draft
---

## O problema

Eu tinha umas vinte versões do meu currículo no Google Docs, cada uma adaptada pra uma vaga diferente, cada uma desatualizada do seu próprio jeito. Adaptar o currículo pra uma vaga nova significava reescrever os tópicos na mão, e as versões foram se afastando aos poucos até se contradizerem.

## O que eu construí

Um repositório onde toda a minha carreira vive em Markdown puro: cada cargo, cada conquista com algumas formas de escrever já aprovadas, habilidades, formação e projetos pessoais. Uma pequena CLI em Python faz o trabalho mecânico. Ela cria uma pasta por candidatura, gera arquivos PDF e Word limpos, de uma coluna só, com pandoc e Typst, e mantém um controle de em que pé está cada candidatura.

Eu adapto cada currículo com o Claude, seguindo uma regra escrita no próprio repositório: toda afirmação precisa ter origem no registro mestre. Reescrever e reordenar pode; números, ferramentas ou cargos novos, não. Quando uma vaga pede algo que eu nunca fiz, isso entra como lacuna na lista em vez de ser preenchido.

Antes de construir, passei por todos os pontos em que meus currículos antigos discordavam e resolvi cada fato, um por um, então o registro mestre é a versão que eu consigo defender numa entrevista.

## Resultado

Adaptar um currículo agora começa de um registro confiável, e não de uma pilha de cópias antigas. Este site é gerado a partir do mesmo registro, então nunca fica desatualizado. Dados pessoais, como meu telefone e as empresas pra onde eu me candidato, ficam fora do repositório.

**Stack:** Python, uv, pandoc, Typst, pytest, Claude
