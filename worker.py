"""Worker privado, sem servidor HTTP. Banco e Storage acessados por TLS.
DATABASE_URL: conexao Postgres/session pooler.
DATABASE_PASSWORD: opcional; senha bruta evita problemas de codificacao na URL.
SUPABASE_URL, SUPABASE_SECRET_KEY: segredos apenas no servidor.
"""
import hashlib,json,os,re,subprocess,sys,tempfile,time,uuid
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

DISCOVER="""
insert into public.pdf_processing_jobs(object_id,object_version,bucket_id,object_path)
select id,coalesce(version,updated_at::text),bucket_id,name from storage.objects
where bucket_id in ('falcao-documentos','familia-documentos') and lower(name) like '%.pdf'
on conflict(object_id,object_version) do nothing
"""
CLAIM="""
with target as (
 select id from public.pdf_processing_jobs
 where (status='queued' and available_at<=now()) or (status='processing' and leased_until<now() and attempts<3)
 order by created_at for update skip locked limit 1
)
update public.pdf_processing_jobs j set status='processing',attempts=attempts+1,lease_token=%s,
leased_until=now()+interval '20 minutes' from target t where j.id=t.id returning j.*
"""

def connection_error_code(error):
    message = str(error).lower()
    for fragment, code in (
        ('password authentication failed', 'database_authentication_failed'),
        ('tenant or user not found', 'database_user_or_project_invalid'),
        ('could not translate host name', 'database_hostname_invalid'),
        ('name or service not known', 'database_hostname_invalid'),
        ('network is unreachable', 'database_network_unreachable_use_session_pooler'),
        ('timeout', 'database_connection_timeout'),
        ('invalid connection option', 'database_url_invalid'),
        ('missing "="', 'database_url_invalid'),
        ('ssl', 'database_tls_error'),
    ):
        if fragment in message:
            return code
    return 'database_connection_error' if isinstance(error, psycopg.OperationalError) else 'processing_error'

def connect():
    password=os.environ.get('DATABASE_PASSWORD')
    if password:
        return psycopg.connect(host='aws-0-us-east-1.pooler.supabase.com',port=5432,
            dbname='postgres',user=os.environ.get('DATABASE_USER','postgres.ijbgupvthfykxnagljzq'),password=password,
            sslmode='require',row_factory=dict_row,connect_timeout=20)
    return psycopg.connect(os.environ['DATABASE_URL'],sslmode='require',row_factory=dict_row,connect_timeout=20)

def current(conn,job):
    return conn.execute("select 1 from storage.objects where id=%s and bucket_id=%s and name=%s and coalesce(version,updated_at::text)=%s",
                        (job['object_id'],job['bucket_id'],job['object_path'],job['object_version'])).fetchone() is not None

def complete(job,status,error=None):
    with connect() as conn:
        conn.execute("update public.pdf_processing_jobs set status=%s,error_code=%s,finished_at=case when %s='queued' then null else now() end,available_at=now()+interval '2 minutes',leased_until=null where id=%s and lease_token=%s and status='processing'",
                     (status,error,status,job['id'],job['lease_token']))

def download(job,dest):
    base=os.environ['SUPABASE_URL'].rstrip('/')
    if base!='https://ijbgupvthfykxnagljzq.supabase.co':raise ValueError('unexpected_project')
    key=os.environ['SUPABASE_SECRET_KEY'];headers={'apikey':key}
    if key.startswith('eyJ'):headers['Authorization']='Bearer '+key
    url=base+'/storage/v1/object/authenticated/'+quote(job['bucket_id'],safe='')+'/'+quote(job['object_path'],safe='/')
    with urlopen(Request(url,headers=headers),timeout=60) as response,dest.open('wb') as f:
        total=0
        while block:=response.read(1024*1024):
            total+=len(block)
            if total>50*1024*1024:raise ValueError('file_too_large')
            f.write(block)

def save(job,result):
    d=result['document'];scope='familia' if job['bucket_id']=='familia-documentos' else 'empresa'
    if d['scope']!=scope:raise ValueError('scope_mismatch')
    with connect() as conn:
        lock=conn.execute("select * from public.pdf_processing_jobs where id=%s for update",(job['id'],)).fetchone()
        if lock['lease_token']!=job['lease_token'] or lock['status']!='processing':return
        if not current(conn,job):
            conn.execute("update public.pdf_processing_jobs set status='superseded',finished_at=now() where id=%s",(job['id'],));return
        conn.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',(scope+':'+d['sha256'],))
        existing=conn.execute('select id from public.pdf_documents where scope=%s and sha256=%s',(scope,d['sha256'])).fetchone()
        if existing:
            doc_id=existing['id']
        else:
            cols=['scope','original_name','report_type','business_classification','sha256','page_count','period_start','period_end','parser_version','status']
            doc_id=conn.execute('insert into public.pdf_documents('+','.join(cols)+',storage_bucket,storage_path) values ('+','.join(['%s']*12)+') returning id',
                        [d.get(k) for k in cols]+[job['bucket_id'],job['object_path']]).fetchone()['id']
            s=result['summary']
            conn.execute('insert into public.pdf_report_summaries(document_id,scope,source_page,metrics,extracted_text,validation_status,validation_details) values (%s,%s,%s,%s,%s,%s,%s)',
                         (doc_id,scope,s['source_page'],Jsonb(s['metrics']),s.get('extracted_text'),s['validation_status'],Jsonb(s['validation_details'])))
            with conn.cursor() as cur:
                cur.executemany('insert into public.pdf_extracted_rows(document_id,scope,source_page,source_row,row_type,data,validation_status) values (%s,%s,%s,%s,%s,%s,%s)',
                  [(doc_id,scope,r['source_page'],r['source_row'],r['row_type'],Jsonb(r['data']),r['validation_status']) for r in result['rows']])
        status='done' if existing or d['status']=='validated' else 'needs_review'
        conn.execute("update public.pdf_processing_jobs set status=%s,document_id=%s,finished_at=now(),leased_until=null,error_code=%s where id=%s",
                     (status,doc_id,'duplicate_content' if existing else None,job['id']))

def process(job):
    with connect() as conn:
        if not current(conn,job):complete(job,'superseded');return
    with tempfile.TemporaryDirectory(prefix='devorador-') as folder:
        source=Path(folder)/'source.pdf';out=Path(folder)/'result.json'
        download(job,source)
        scope='familia' if job['bucket_id']=='familia-documentos' else 'empresa'
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        with connect() as conn:
            if not current(conn,job):complete(job,'superseded');return
            existing=conn.execute('select id from public.pdf_documents where scope=%s and sha256=%s',(scope,digest)).fetchone()
        if existing:
            save(job,{'document':{'scope':scope,'sha256':digest,'status':'validated'}});return
        try:
            run=subprocess.run([sys.executable,str(Path(__file__).with_name('parse_job.py')),str(source),scope,Path(job['object_path']).name,str(out)],
                               timeout=900,capture_output=True)
        except subprocess.TimeoutExpired:
            complete(job,'needs_review','parser_timeout');return
        if run.returncode:
            code=run.stderr.decode(errors='ignore').strip().splitlines()[-1] if run.stderr else 'parser_error'
            safe=bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',code))
            complete(job,'needs_review',code if safe else 'parser_error');return
        result=json.loads(out.read_text(encoding='utf-8'))
        if result['document']['sha256']!=digest:raise ValueError('digest_mismatch')
        save(job,result)

def main():
    for key in ('DATABASE_URL','SUPABASE_URL','SUPABASE_SECRET_KEY'):
        if not os.environ.get(key):raise SystemExit('Missing environment variable: '+key)
    while True:
        job=None
        try:
            with connect() as conn:
                conn.execute(DISCOVER)
                conn.execute("update public.pdf_processing_jobs set status='failed',error_code='lease_expired',finished_at=now() where status='processing' and leased_until<now() and attempts>=3")
                job=conn.execute(CLAIM,(uuid.uuid4(),)).fetchone()
            if job:
                process(job)
                print(json.dumps({'job':str(job['id']),'event':'handled'}),flush=True)
            else:time.sleep(30)
        except Exception as e:
            # Nao registrar URLs, segredos, consultas ou conteudo dos PDFs.
            print(json.dumps({'event':'error','type':type(e).__name__,'code':connection_error_code(e)}),flush=True)
            if job:
                try:complete(job,'queued' if job['attempts']<3 else 'failed',type(e).__name__)
                except Exception:pass
            time.sleep(30)

if __name__=='__main__':main()
