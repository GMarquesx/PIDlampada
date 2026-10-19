# Esquema elétrico em LaTeX (PIDL-ESQ-001 Rev. D)

Versão em LaTeX/circuitikz do esquema elétrico, com as mesmas 3 folhas A3 da
versão em Python: moldura com zonas 1-8 / A-F, carimbo, tabela de revisões,
blocos [1] a [10], redes, pinagem, notas de projeto e lista de materiais.

| Arquivo | O que é |
|---|---|
| `esquema_eletrico.tex` | Fonte LaTeX, independente: pode editar à mão |
| `Esquema_Eletrico_Rev_D_LaTeX.pdf` | O PDF compilado |
| `gerar_tex.py` | Regera o `.tex` a partir de `../esquema_dados.py` (tabelas, revisões, BOM) |

Compilar (TeX Live ou MiKTeX, pacotes `circuitikz`, `tabularx`, `helvet`):

```powershell
cd docs\hardware\latex
pdflatex esquema_eletrico.tex
pdflatex esquema_eletrico.tex   # segunda passada: posiciona a prancha na página
```

Atenção: `gerar_tex.py` sobrescreve o `.tex`. Se editar o `.tex` à mão, não
rode o gerador depois (ou leve a mudança para o gerador).
