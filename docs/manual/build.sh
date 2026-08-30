#!/usr/bin/env bash
#
# Build the manual, and refuse to finish on a half-built document.
#
# LaTeX resolves cross-references and the table of contents by writing .aux and
# .toc on one pass and reading them on the next, so the first pass legitimately
# reports every reference as undefined. pdflatex exits non-zero when it does,
# which stops a naive build after that first pass and leaves a PDF full of "??"
# and an empty Contents -- one of which was committed. Iterate, then check.
set -uo pipefail
cd "$(dirname "$0")"

for pass in 1 2 3; do
    pdflatex -interaction=nonstopmode radcoolpv_manual.tex > /dev/null 2>&1
done

fail=0
if grep -q "^!" radcoolpv_manual.log; then
    echo "LaTeX errors:" >&2
    grep -A2 "^!" radcoolpv_manual.log >&2
    fail=1
fi
if grep -q "There were undefined references" radcoolpv_manual.log; then
    echo "Undefined references remain after three passes:" >&2
    grep "LaTeX Warning: Reference" radcoolpv_manual.log >&2
    fail=1
fi
if [ ! -s radcoolpv_manual.toc ]; then
    echo "The table of contents is empty." >&2
    fail=1
fi

pages=$(grep -o "([0-9]* pages" radcoolpv_manual.log | tail -1 | tr -d '(')
rm -f radcoolpv_manual.{aux,log,out,toc,fls,fdb_latexmk}
[ "$fail" -eq 0 ] && echo "==> radcoolpv_manual.pdf, ${pages}, no unresolved references"
exit "$fail"
