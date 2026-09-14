"""Extrator REL1136 Command. Requer pdfplumber==0.11.8.
Uso: python devorador_produtos.py arquivo.pdf. Saida JSON sem acesso a rede.
Preserva custo total impresso: custo unitario arredondado pode nao reproduzi-lo.
"""
import json,re,sys,hashlib
from pathlib import Path
from decimal import Decimal
import pdfplumber

def money(s):
    s=re.sub(r'\s+','',s)
    if not re.fullmatch(r'-?[\d.]+,\d{2}',s): raise ValueError('Valor invalido: '+s)
    return format(Decimal(s.replace('.','').replace(',','.')),'.2f')

def extract(path):
    rows=[];checks=[];classe=None;class_sum=Decimal(0)
    with pdfplumber.open(path) as pdf:
        first=pdf.pages[0].extract_text()
        reference=re.search(r'Data Específica\s*:\s*(\d{2}/\d{2}/\d{4})',first)[1]
        for pn,page in enumerate(pdf.pages,1):
            events=[]
            for w in page.extract_words():
                if w['text'] in ('A','I') and 548<w['x0']<555: events.append((w['top'],'row',w))
                elif w['text']=='Classe' and w['x0']<40: events.append((w['top'],'class',w))
                elif w['text']=='Total' and w['top']>45: events.append((w['top'],'total',w))
            events.sort()
            for ix,(y,kind,w) in enumerate(events):
                def get(a,b,end=None):
                    cs=[c for c in page.chars if a<=(c['x0']+c['x1'])/2<b and y-1<=c['top']<(y+2 if end is None else end)]
                    lines={}
                    for c in cs:
                        key=next((k for k in lines if abs(k-c['top'])<2),c['top'])
                        lines.setdefault(key,[]).append(c)
                    return ' '.join(''.join(c['text'] for c in sorted(lines[k],key=lambda c:c['x0'])) for k in sorted(lines)).strip()
                if kind=='class': classe=get(30,560)
                elif kind=='row':
                    if classe is None: raise ValueError('Classe ausente')
                    end=events[ix+1][0]-1 if ix+1<len(events) else min(page.height-40,y+35)
                    data=dict(codigo=get(30,125),descricao=get(125,345,end),unidade=get(345,380),saldo=money(get(380,432)),
                              ultimo_custo=money(get(432,490)),custo_total=money(get(490,545)),situacao=w['text'],classe=classe,data_especifica=reference)
                    if not data['codigo']: raise ValueError('Codigo ausente')
                    rows.append(dict(source_page=pn,source_row=sum(r['source_page']==pn for r in rows)+1,row_type='produto_estoque',data=data,validation_status='passed'))
                    class_sum+=Decimal(data['custo_total'])
                elif kind=='total':
                    text=get(30,565)
                    if 'Total da Classe' in text:
                        printed=Decimal(money(get(490,595,y+7)))
                        checks.append(dict(classe=classe,printed=str(printed),calculated=str(class_sum),passed=printed==class_sum));class_sum=Decimal(0)
        line=next(l for l in pdf.pages[-1].extract_text().splitlines() if 'Total Geral' in l)
        total=money(re.findall(r'\d[\d.]*,\d{2}',line)[-1])
        calculated=format(sum((Decimal(r['data']['custo_total']) for r in rows),Decimal(0)),'.2f')
        passed=total==calculated and all(c['passed'] for c in checks)
        if not passed:
            for row in rows: row['validation_status']='needs_review'
        return dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=rows,validation=dict(passed=passed,row_count=len(rows),printed=total,calculated=calculated,class_checks=checks,
                    limitations=['Data especifica impressa: '+reference+'; posterior a emissao de 13/09/2026. Confirmar significado antes de analises temporais.',
                                 'Saldos em unidades distintas nao devem ser somados como uma quantidade homogenea.',
                                 'Custo total impresso preservado; ultimo custo unitario pode estar arredondado.']))

if __name__=='__main__': print(json.dumps(extract(Path(sys.argv[1])),ensure_ascii=False))
