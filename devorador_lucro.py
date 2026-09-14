"""Extrator Command lucro bruto, pdfplumber==0.11.8.
Uso: python devorador_lucro.py arquivo.pdf [saida.json]. Sem acesso a rede.
Preserva valores impressos e discrepancias de arredondamento.
"""
import json,re,sys,hashlib
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import pdfplumber

def money(s):
    s=re.sub(r'\s+','',s)
    if not re.fullmatch(r'-?[\d.]+,\d{2}',s):raise ValueError('Valor ilegivel: '+s)
    return format(Decimal(s.replace('.','').replace(',','.')),'.2f')

def extract(path):
    rows=[]
    with pdfplumber.open(path) as pdf:
        for pn,page in enumerate(pdf.pages,1):
            if abs(page.width-595.5)>2:raise ValueError('Layout desconhecido')
            anchors=[w for w in page.extract_words() if 29<w['x0']<32 and re.fullmatch(r'\d{2}/\d{2}/\d{4}',w['text'])]
            totals=[w for w in page.extract_words() if w['text'].startswith('Totalização')]
            for idx,w in enumerate(anchors):
                y=w['top']; end=anchors[idx+1]['top']-1 if idx+1<len(anchors) else (totals[0]['top']-1 if totals else page.height-45)
                cs=[c for c in page.chars if y-1<=c['top']<end]
                def get(a,b,first=False):
                    lines={}
                    for c in cs:
                        if not a<=(c['x0']+c['x1'])/2<b or (first and abs(c['top']-y)>2):continue
                        k=next((k for k in lines if abs(k-c['top'])<2),c['top'])
                        lines.setdefault(k,[]).append(c)
                    return ' '.join(''.join(c['text'] for c in sorted(lines[k],key=lambda c:c['x0'])) for k in sorted(lines)).strip()
                seller=get(153,219)
                action=get(153,219,True)
                data=dict(data=datetime.strptime(w['text'],'%d/%m/%Y').date().isoformat(),nota=get(80,153,True),
                          acao_comercial=action,vendedor=seller[len(action):].strip(),cliente=get(219,335),
                          custo=money(get(335,395,True)),total_liquido=money(get(395,455,True)),lucro_bruto=money(get(455,513,True)))
                if not re.fullmatch(r'MA\d{4}/\d+',data['nota']):raise ValueError('Nota ilegivel: '+data['nota'])
                delta=Decimal(data['total_liquido'])-Decimal(data['custo'])-Decimal(data['lucro_bruto'])
                data['diferenca_aritmetica']=str(delta)
                rows.append(dict(source_page=pn,source_row=idx+1,row_type='operacao_lucro_bruto',data=data,validation_status='pending'))
        last=pdf.pages[-1];anchor=next(w for w in last.extract_words() if w['text'].startswith('Totalização'));y=anchor['top']
        def total(a,b):
            cs=[c for c in last.chars if a<=(c['x0']+c['x1'])/2<b and y-1<=c['top']<y+14]
            return money(''.join(c['text'] for c in sorted(cs,key=lambda c:(c['top'],c['x0']))))
        printed={k:total(a,b) for k,a,b in [('custo',335,395),('total_liquido',395,455),('lucro_bruto',455,520)]}
        calculated={k:format(sum((Decimal(r['data'][k]) for r in rows),Decimal(0)),'.2f') for k in printed}
        passed=printed==calculated
        for row in rows:row['validation_status']='passed' if passed and Decimal(row['data']['diferenca_aritmetica'])==0 else 'needs_review'
        return dict(original_name=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=rows,
                    validation=dict(passed=passed,row_count=len(rows),printed=printed,calculated=calculated,
                    differences={k:str(Decimal(calculated[k])-Decimal(printed[k])) for k in printed},
                    rows_arithmetic_difference=sum(Decimal(r['data']['diferenca_aritmetica'])!=0 for r in rows),
                    limitations=['Criterio do relatorio: ultimo custo; nao equivale necessariamente ao custo contabil historico.',
                                 'Lucro bruto nao e lucro liquido. Percentual deve ser calculado com denominador explicito.',
                                 'Comparacoes anuais devem respeitar cobertura parcial de 2026.']))

if __name__=='__main__':
    result=json.dumps(extract(Path(sys.argv[1])),ensure_ascii=False)
    if len(sys.argv)>2:Path(sys.argv[2]).write_text(result,encoding='utf-8')
    else:print(result)
