"""Primeira etapa do Devorador: catalogo e totalizacoes dos modelos Command.

Requer pdfplumber==0.11.8. Uso: python devorador_resumos.py PASTA
Imprime JSON; nao envia arquivos nem altera o Supabase.
Valores monetarios sao strings decimais para preservar centavos.
Este modulo NAO valida a soma do detalhamento, nem gera embeddings.
"""
import hashlib
import json
import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import pdfplumber

VERSION = 'command-summary-0.1.0'

def money(s):
    s = re.sub(r'\s+', '', s)
    if not re.fullmatch(r'-?(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2}', s):
        raise ValueError('Valor monetario invalido: ' + repr(s))
    return format(Decimal(s.replace('.', '').replace(',', '.')), '.2f')

def cell(page, left, right, top, height):
    chars = [c for c in page.chars if left <= (c['x0']+c['x1'])/2 < right
             and top-1 <= c['top'] < top+height]
    lines = {}
    for c in sorted(chars, key=lambda c: (c['top'], c['x0'])):
        key = next((y for y in lines if abs(y-c['top']) < 2), c['top'])
        lines.setdefault(key, []).append(c)
    return ''.join(''.join(c['text'] for c in sorted(lines[y], key=lambda c: c['x0']))
                   for y in sorted(lines))

def process(path):
    name = path.name
    scope = 'familia' if name.startswith('Despesa Remy ') else 'empresa'
    kind = ('despesas' if name.startswith('Despesa ') else
            'lucro_bruto' if name.startswith('Analise de Lucro Bruto') else
            'titulos_abertos' if name.startswith('Inadimplentes ') else
            'produtos' if name.startswith('Listagem de Produtos') else None)
    if kind is None:
        raise ValueError('Modelo nao cadastrado: '+name)
    with pdfplumber.open(path) as pdf:
        first = pdf.pages[0].extract_text() or ''
        last = pdf.pages[-1]
        text = last.extract_text() or ''
        dates = re.search(r'(?:Período de|Data de Vencimento de|Período de Vencimento de) (\d{2}/\d{2}/\d{4}) [aà] (\d{2}/\d{2}/\d{4})', first)
        if not dates and kind == 'produtos':
            dates = re.search(r'Data Específica\s*:\s*(\d{2}/\d{2}/\d{4})',first)
        iso = lambda d: datetime.strptime(d,'%d/%m/%Y').date().isoformat()
        doc = dict(original_name=name,scope=scope,report_type=kind,
                   sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   page_count=len(pdf.pages),parser_version=VERSION,status='registered',
                   period_start=iso(dates[1]) if dates else None,
                   period_end=iso(dates[2] if dates.lastindex==2 else dates[1]) if dates else None,
                   business_classification=name.rsplit('.pdf',1)[0])
        metrics = {}
        notes = ['Total impresso extraido; soma de todas as operacoes ainda nao conferida.',
                 'PDF original ainda nao enviado ao Storage.']
        if kind in ('lucro_bruto','despesas'):
            anchor = next(w for w in last.extract_words() if w['text'].startswith('Totalização'))
            y=anchor['top']
            if kind=='lucro_bruto':
                if abs(last.width-595.5)>2: raise ValueError('Layout de lucro desconhecido')
                cols=[('custo',335,395),('total_liquido',395,455),('lucro_bruto',455,520),('percentual_sobre_custo',525,568)]
                metrics={k:money(cell(last,a,b,y,14)) for k,a,b in cols}
                if Decimal(metrics['custo'])+Decimal(metrics['lucro_bruto'])!=Decimal(metrics['total_liquido']):
                    raise ValueError('Total liquido difere de custo mais lucro')
                notes.append('Identidade custo + lucro = total liquido conferida.')
                notes.append('Percentual impresso usa custo como denominador. Criterio: ultimo custo.')
            else:
                if abs(last.width-842.25)>2: raise ValueError('Layout de despesas desconhecido')
                cols=[('principal',678,722),('baixado',722,770),('liquido',770,815)]
                metrics={k:money(cell(last,a,b,y,13)) for k,a,b in cols}
                notes.append('Periodo por vencimento; baixado nao equivale a fluxo de caixa por data do pagamento.')
        elif kind=='titulos_abertos':
            line=next(l for l in text.splitlines() if 'Total Geral:' in l)
            amounts=re.findall(r'\d[\d.]*,\d{2}',line)
            if len(amounts)!=2: raise ValueError('Total de titulos ambiguo')
            metrics=dict(vencido=money(amounts[0]),a_vencer=money(amounts[1]))
        else:
            line=next(l for l in text.splitlines() if 'Total Geral' in l)
            amounts=re.findall(r'\d[\d.]*,\d{2}',line)
            if len(amounts)!=1: raise ValueError('Total de produtos ambiguo')
            metrics={'custo_total':money(amounts[0])}
            notes.append('Estoque: nao representa produtos vendidos. Data especifica preservada como impressa.')
        return {'document':doc,'summary':dict(source_page=len(pdf.pages),metrics=metrics,
                validation_status='pending',validation_details={'notes':notes},extracted_text=text)}

if __name__=='__main__':
    result=[]
    for p in sorted(Path(sys.argv[1]).glob('*.pdf')):
        result.append(process(p))
    print(json.dumps(result,ensure_ascii=False))
