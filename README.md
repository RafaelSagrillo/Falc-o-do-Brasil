# Devorador de PDF — processamento automatico

Worker privado para o projeto ijbgupvthfykxnagljzq. Nao abre portas HTTP.

## Ativacao

1. A tabela da fila deve estar criada no Supabase (queue.sql).
2. Hospedar esta pasta como um servico Docker persistente no Railway, com uma replica.
3. Configurar no servidor DATABASE_URL (conexao Session pooler do Supabase),
   SUPABASE_URL=https://ijbgupvthfykxnagljzq.supabase.co e SUPABASE_SECRET_KEY
   (chave secreta do projeto, ou service_role legado).
   Inserir os segredos diretamente nas variaveis privadas do servidor; nunca em chat ou Git.
4. Enviar um novo PDF de teste e conferir pdf_processing_jobs e os totais importados.

Esta versao ainda precisa de teste integrado com credenciais no servidor.
Nao afirmar que a automacao esta ativa antes disso.

## Comportamento

Verifica a cada 30 segundos os dois buckets privados, incluindo subpastas.
Identifica versoes de objetos, usa reserva de tarefa de 20 minutos e tres tentativas
para falhas transitorias. Leitura isolada em subprocesso com limite de 15 minutos.
Documento, resumo e linhas sao gravados numa unica transacao. Arquivos identicos
no mesmo escopo sao reconhecidos pelo SHA-256. Uma substituicao durante a leitura
invalida a tarefa antiga. Use um nome novo por envio para preservar o PDF historico:
Storage nao preserva automaticamente o conteudo antigo de um arquivo sobrescrito.

Empresa e familia sao definidas pelo bucket; filtros do cabecalho das despesas
devem concordar. O nome do arquivo nao define mais o tipo de relatorio.
PDF sem texto, layout desconhecido, campos ilegíveis ou timeout ficam para revisao.
Nao inclui OCR nem envio de cobrancas.

Valores impressos e divergencias sao mantidos. Relatorios sobrepostos permanecem
como retratos separados: a interface futura deve selecionar um retrato para evitar
somar a mesma divida/venda em varios documentos. Nao efetua baixa automatica.

O worker utiliza uma conexao administrativa no servidor. Nenhuma permissao de
acesso foi concedida a usuarios anonimos ou usuarios do aplicativo.

## Interface do aplicativo

A proxima etapa e um frontend separado em React para envio de PDFs,
acompanhamento do processamento, consulta dos dados e relatorios.

O acabamento visual usara React Spring para animacoes discretas: entrada de
indicadores e graficos, abertura de detalhes de documentos, estados de
processamento e transicoes de filtros. A dependencia sera instalada junto com
o projeto frontend, quando existirem os arquivos `package.json` e a primeira
tela; este worker Python nao possui frontend em que ela possa ser usada ainda.
