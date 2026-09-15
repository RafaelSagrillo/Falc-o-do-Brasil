----------------------------------------------------------------------
Ran 4 tests in 2.324s

OK
"""Leitor dos tres modelos de titulos em aberto Command. pdfplumber==0.11.8.
Uso: python devorador_inadimplencia.py pasta. Saida JSON, sem acesso a rede.
Conserva documento/parcela como impressos: identificadores podem estar truncados.
"""
import json,re,hashlib,sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import pdfplumber

def amount(s):
    compact=re.sub(r'\s+','',s).replace('R$','')
    if not compact or compact in ('-','--'): return '0.00'
    values=re.findall(r'-?\d[\d.]*,\d{2}',compact)
    if len(values)!=1: raise ValueError('Valor ilegivel')
    return format(Decimal(values[0].replace('.','').replace(',','.')),'.2f')

def extract(path):
    rows=[];checks=[];seller=None;person=None
    person_sum=[Decimal(0),Decimal(0)];seller_sum=[Decimal(0),Decimal(0)]
    with pdfplumber.open(path) as pdf:
        first=pdf.pages[0].extract_text()
        reference=datetime.strptime(re.search(r'\d{2}/\d{2}/\d{4}',first)[0],'%d/%m/%Y').date()
        for pn,page in enumerate(pdf.pages,1):
            if abs(page.width-595.5)>2: raise ValueError('Layout desconhecido')
            words=page.extract_words(); events=[]
            for w in words:
                t=w['text'];x=w['x0']
                if t=='Vendedor:' and x<40: events.append((w['top'],'seller',w))
                elif re.fullmatch(r'\d{6}',t) and x<40: events.append((w['top'],'person',w))
                elif re.fullmatch(r'\d{2}/\d{2}/\d{2}',t) and 220<x<225: events.append((w['top'],'title',w))
                elif t=='Total' and x>340: events.append((w['top'],'total',w))
            for y,kind,w in sorted(events):
                def get(a,b,height=2):
                    cs=[c for c in page.chars if a<=(c['x0']+c['x1'])/2<b and y-1.8<=c['top']<y+height]
                    lines={}
                    for c in sorted(cs,key=lambda c:(c['top'],c['x0'])):
                        key=next((k for k in lines if abs(k-c['top'])<2),c['top'])
                        lines.setdefault(key,[]).append(c)
                    return ' '.join(''.join(c['text'] for c in sorted(lines[k],key=lambda c:c['x0'])) for k in sorted(lines)).strip()
                if kind=='seller':
                    seller=get(77,565)
                elif kind=='person':
                    person=dict(cliente_codigo=w['text'],razao_social=get(98,285,height=12),nome_fantasia=get(285,457,height=12))
                elif kind=='title':
                    if person is None or seller is None: raise ValueError('Titulo sem contexto')
                    issue_raw=get(178,220)
                    issue=datetime.strptime(issue_raw,'%d/%m/%y').date() if re.fullmatch(r'\d{2}/\d{2}/\d{2}',issue_raw) else None
                    due=datetime.strptime(get(220,261),'%d/%m/%y').date()
                    vencido=amount(get(460,521));a_vencer=amount(get(521,567))
                    data={**person,'vendedor':seller,'empresa_codigo':get(110,123),'documento_parcela_impresso':get(123,178),
                          'emissao':issue.isoformat() if issue else None,'emissao_texto_impresso':issue_raw,'revisar_identificacao':issue is None,'vencimento':due.isoformat(),'dias_impressos':get(261,282),
                          'dias_calculados':(reference-due).days,'data_referencia':reference.isoformat(),
                          'tipo_documento':get(282,383),'vencido':vencido,'a_vencer':a_vencer}
                    rows.append(dict(source_page=pn,source_row=sum(r['source_page']==pn for r in rows)+1,row_type='titulo_a_receber',data=data,validation_status='passed' if issue else 'needs_review'))
                    for i,v in enumerate([vencido,a_vencer]): person_sum[i]+=Decimal(v);seller_sum[i]+=Decimal(v)
                elif kind=='total':
                    label=get(340,455)
                    printed=[Decimal(amount(get(460,521))),Decimal(amount(get(521,567)))]
                    if 'Pessoa' in label: calculated=person_sum[:];person_sum=[Decimal(0),Decimal(0)]
                    elif 'Vendedor' in label: calculated=seller_sum[:];seller_sum=[Decimal(0),Decimal(0)]
                    elif 'Geral' in label: calculated=[sum((Decimal(r['data'][k]) for r in rows),Decimal(0)) for k in ['vencido','a_vencer']]
                    else: continue
                    checks.append(dict(page=pn,label=label,passed=printed==calculated,printed=list(map(str,printed)),calculated=list(map(str,calculated))))
        passed=bool(checks) and any('Geral' in c['label'] for c in checks) and all(c['passed'] for c in checks)
        if not passed:
            for r in rows:r['validation_status']='needs_review'
        return dict(original_name=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=rows,
                    validation=dict(passed=passed,row_count=len(rows),identification_review_count=sum(r['data']['revisar_identificacao'] for r in rows),checks=checks,
                    limitations=['Documento/parcela pode estar truncado no PDF; nao e chave global segura.',
                                 'Cada relatorio e um retrato na data de referencia. Nao somar retratos sobrepostos.',
                                 'Classificacao perdidos preservada; nao implica baixa contabil.']))

if __name__=='__main__':
    print(json.dumps([extract(p) for p in sorted(Path(sys.argv[1]).glob('Inadimplentes*.pdf'))],ensure_ascii=False))
