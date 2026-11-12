// Pandoc Typst template for resumes and cover letters: single column, real text, ATS-safe.
#let horizontalRule = line(length: 100%, stroke: 0.4pt)
#let divider = horizontalRule

#set document(title: "$pagetitle$")
#set page(paper: "a4", margin: (x: 1.6cm, y: 1.5cm))
#set text(font: ("Calibri", "Arial", "Microsoft YaHei"), size: 10pt, lang: "$if(lang)$$lang$$else$en$endif$")
#set par(justify: false, leading: 0.55em, spacing: 0.7em)
#set list(indent: 0.6em, body-indent: 0.5em, spacing: 0.45em)
#set heading(numbering: none)
#show link: it => it
#show heading.where(level: 1): it => block(below: 0.4em, text(size: 18pt, weight: "bold", it.body))
#show heading.where(level: 2): it => block(above: 1.1em, below: 0.5em, width: 100%)[
  #text(size: 11pt, weight: "bold", upper(it.body))
  #v(-0.6em)
  #line(length: 100%, stroke: 0.4pt)
]
#show heading.where(level: 3): it => block(above: 0.8em, below: 0.35em, text(size: 10.5pt, weight: "bold", it.body))

$if(highlighting-definitions)$
$highlighting-definitions$
$endif$

$body$
