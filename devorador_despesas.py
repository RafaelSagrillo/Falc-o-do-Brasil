"""Extrai titulos do modelo REL0978 Command, sem acesso a rede.

Requer pdfplumber==0.11.8. Uso: python devorador_despesas.py pasta_dos_pdfs
Saida JSON em stdout. Valores em strings decimais; datas por vencimento.
Campos cortados no PDF sao preservados, nunca completados por inferencia.
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import pdfplumber

VERSION='command-expenses-0.1.0'

def money(value):
    value=re.sub(r'\s+','',value)
    if not re.fullmatch(r'-?(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2}',value):
        raise ValueError('Valor monetario ilegivel: '+repr(value))
    return format(Decimal(value.replace('.','').replace(',','.')),'.2f')

def cell(chars,left,right):
    chosen=[c for c in chars if left <= (c['x0']+c['x1'])/2 < right]
    lines={}
    for c in sorted(chosen,key=lambda c:(c['top'],c['x0'])):
        y=next((y for y in lines if abs(y-c['top'])<2),c['top'])
        lines.setdefault(y,[]).append(c)
    return ''.join(''.join(c['text'] for c in sorted(lines[y],key=lambda c:c['x0'])) for y in sorted(lines)).strip()

def extract(path):
    scope='familia' if path.name.startswith('Despesa Remy ') else 'empresa'
    if not (path.name.startswith('Despesa Remy ') or path.name.startswith('Despesa Falcao ')):
        raise ValueError('Arquivo nao reconhecido')
    rows=[]
    with pdfplumber.open(path) as pdf:
        first=pdf.pages[0].extract_text()
        expected_filter='DESPESA FIXA REMY' if scope=='familia' else 'DESPESA FIXA FALCAO'
        if expected_filter not in first or 'Relação de Títulos a Pagar' not in first:
            raise ValueError('Cabecalho diverge da classificacao')
        period=re.search(r'Data de Vencimento de (\d{2}/\d{2}/\d{4}) a (\d{2}/\d{2}/\d{4})',first)
        start,end=[datetime.strptime(v,'%d/%m/%Y').date() for v in period.groups()]
        for page_number,page in enumerate(pdf.pages,1):
            if abs(page.width-842.25)>2: raise ValueError('Layout desconhecido')
            words=page.extract_words()
            anchors=[w for w in words if 40<w['x0']<50 and re.fullmatch(r'\d{2}/\d{2}/\d{2}',w['text'])]
            for row_number,w in enumerate(anchors,1):
                chars=[c for c in page.chars if abs(c['top']-w['top'])<2]
                get=lambda a,b:cell(chars,a,b)
                issue=datetime.strptime(get(40,80),'%d/%m/%y').date()
                due=datetime.strptime(get(80,120),'%d/%m/%y').date()
                if not start<=due<=end: raise ValueError('Vencimento fora do filtro')
                seq_person=get(120,454)
                match=re.fullmatch(r'(\d+/\d+)(.*)',seq_person)
                if not match: raise ValueError('Parcela nao identificada')
                title=get(475,540)
                if not re.fullmatch(r'MA\d{4}/\d+',title): raise ValueError('Titulo nao reconhecido: '+title)
                data=dict(emissao=issue.isoformat(),vencimento=due.isoformat(),parcela=match[1],
                          pessoa=match[2].strip(),aceite=get(454,475),titulo=title,documento=get(540,675),
                          principal=money(get(675,722)),baixado=money(get(722,770)),liquido=money(get(770,815)))
                rows.append(dict(source_page=page_number,source_row=row_number,row_type='titulo_a_pagar',
                                 data=data,raw_text=get(30,815),validation_status='passed'))
        last=pdf.pages[-1]
        y=next(w['top'] for w in last.extract_words() if w['text']=='Totalização:')
        chars=[c for c in last.chars if y-1<=c['top']<y+13]
        totals={k:money(cell(chars,a,b)) for k,a,b in [('principal',678,722),('baixado',722,770),('liquido',770,815)]}
        sums={k:format(sum((Decimal(r['data'][k]) for r in rows),Decimal(0)),'.2f') for k in totals}
        passed=totals==sums
        if not passed:
            for row in rows: row['validation_status']='needs_review'
        return dict(original_name=path.name,scope=scope,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    parser_version=VERSION,rows=rows,validation=dict(passed=passed,row_count=len(rows),
                    printed=totals,calculated=sums,period_start=start.isoformat(),period_end=end.isoformat(),
                    limitations=['Periodo por vencimento, nao por data de pagamento.',
                                 'Somente DESPESA FIXA conforme filtro do PDF; nao e toda a despesa da entidade.',
                                 'Somas reconciliadas; descricoes preservadas como impressas, inclusive truncamentos.']))

if __name__=='__main__':
    print(json.dumps([extract(p) for p in sorted(Path(sys.argv[1]).glob('Despesa*.pdf'))],ensure_ascii=False))
