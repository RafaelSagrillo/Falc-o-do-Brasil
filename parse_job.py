"""Isolamento do parser. Executado em subprocesso com tempo limite pelo worker."""
import json,sys,shutil,re,unicodedata
from pathlib import Path
import pdfplumber
import devorador_resumos as summary
import devorador_despesas as expenses
import devorador_inadimplencia as receivables
import devorador_lucro as profit
import devorador_produtos as products

def classify(header,scope,original_name=''):
    normalized=' '.join(unicodedata.normalize('NFKD',header).encode('ascii','ignore').decode().upper().split())
    normalized_name=' '.join(unicodedata.normalize('NFKD',original_name).encode('ascii','ignore').decode().upper().split())
    if 'RELACAO DE TITULOS A PAGAR' in normalized:
        if 'DESPESA FIXA REMY' in normalized:
            if scope!='familia':raise ValueError('scope_mismatch')
            return 'Despesa Remy novo.pdf',expenses.extract
        if 'DESPESA FIXA FALCAO' in normalized:
            if scope!='empresa':raise ValueError('scope_mismatch')
            return 'Despesa Falcao novo.pdf',expenses.extract
    if scope!='empresa':raise ValueError('unsupported_family_report')
    if 'ANALISE DO LUCRO BRUTO' in normalized:return 'Analise de Lucro Bruto - novo.pdf',profit.extract
    if 'TITULOS EM ABERTO' in normalized and ('TITULOS A RECEBER' in normalized or 'A RECEBER' in normalized):
        return 'Inadimplentes novo.pdf',receivables.extract
    if scope=='empresa' and ('INADIMPLENCIA' in normalized_name or 'INADIMPLENTES' in normalized_name):
        return 'Inadimplentes novo.pdf',receivables.extract
    if 'LISTAGEM DE PRODUTO POR ULTIMO CUSTO' in normalized:return 'Listagem de Produtos novo.pdf',products.extract
    raise ValueError('unsupported_report')

def parse(source,scope,original_name):
    with pdfplumber.open(source) as pdf:
        header=pdf.pages[0].extract_text() or ''
        if not header:raise ValueError('ocr_required')
    name,extractor=classify(header,scope,original_name)
    canonical=source.parent/name
    shutil.copyfile(source,canonical)
    out=summary.process(canonical)
    detail=extractor(canonical)
    out['document']['original_name']=original_name
    out['document']['business_classification']=header[:2000]
    out['document']['scope']=scope
    out['document']['parser_version']='automatic-0.1.0'
    out['rows']=detail['rows']
    out['validation']=detail['validation']
    out['summary']['validation_details']=detail['validation']
    clean=detail['validation']['passed'] and all(r['validation_status']=='passed' for r in detail['rows'])
    out['summary']['validation_status']='passed' if clean else 'needs_review'
    out['document']['status']='validated' if clean else 'needs_review'
    return out

if __name__=='__main__':
    try:
        result=parse(Path(sys.argv[1]),sys.argv[2],sys.argv[3])
        Path(sys.argv[4]).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    except Exception as e:
        # Nao enviar conteudo financeiro para logs da hospedagem.
        safe_codes={'scope_mismatch','unsupported_family_report','unsupported_report','ocr_required'}
        code=str(e) if isinstance(e,ValueError) and str(e) in safe_codes else type(e).__name__
        print(code,file=sys.stderr)
        sys.exit(2)
