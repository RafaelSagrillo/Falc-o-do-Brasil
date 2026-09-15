"""Isolamento do parser. Executado em subprocesso com tempo limite pelo worker."""
import hashlib,json,sys,shutil,re,unicodedata
from decimal import Decimal
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
    detail=extractor(canonical)
    try:
        out=summary.process(canonical)
    except StopIteration:
        if extractor is not receivables.extract:
            raise
        rows=detail['rows']
        with pdfplumber.open(canonical) as pdf:
            page_count=len(pdf.pages)
            last_text=pdf.pages[-1].extract_text() or ''
        due_dates=sorted(r['data']['vencimento'] for r in rows)
        metrics={key:format(sum((Decimal(r['data'][key]) for r in rows),Decimal(0)),'.2f')
                 for key in ('vencido','a_vencer')}
        out={'document':dict(original_name=canonical.name,scope=scope,report_type='titulos_abertos',
              sha256=hashlib.sha256(canonical.read_bytes()).hexdigest(),page_count=page_count,
              parser_version=summary.VERSION,status='registered',
              period_start=due_dates[0] if due_dates else None,period_end=due_dates[-1] if due_dates else None,
              business_classification=canonical.stem),
             'summary':dict(source_page=page_count,metrics=metrics,extracted_text=last_text,
              validation_status='pending',validation_details={'notes':['Resumo calculado pelas parcelas; linha Total Geral ausente.']})}
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
        message=str(e)
        if isinstance(e,ValueError) and message in safe_codes: code=message
        elif isinstance(e,ValueError) and message.startswith('Layout desconhecido'): code='receivables_layout_unknown'
        elif isinstance(e,ValueError) and message.startswith('Titulo sem contexto'): code='receivables_context_missing'
        elif isinstance(e,ValueError) and message.startswith('Valor ilegivel'): code='receivables_amount_format'
        elif isinstance(e,ValueError) and 'does not match format' in message: code='receivables_date_format'
        else: code=type(e).__name__
        print(code,file=sys.stderr)
        sys.exit(2)
