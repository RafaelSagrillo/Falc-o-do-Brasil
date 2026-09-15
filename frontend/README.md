# Falcão do Brasil — painel de gestão

Primeira versão navegável da interface, criada em React. Inclui React Spring,
Recharts e importação CSV validada. O processamento Python existente continua
independente desta pasta.

## Executar

```sh
npm ci
npm run dev
npm run test
npm run build
npm start
```

O servidor de produção usa `PORT` (padrão 3000). Em Railway, configure a raiz
do serviço como `/frontend`, Dockerfile `Dockerfile`, healthcheck `/health`.
Não copie as variáveis privadas do processador PDF para este serviço.

## Funcionalidades desta versão

- Painel responsivo: visão geral, desempenho, vendas, documentos e relatórios.
- Frasco sem marca, óleo âmbar, movimento de rolagem e trilhas nas laterais.
- Gráficos interativos, seleção de ano e semestre, empresa/família separados.
- CSV mensal com prévia e validação: os exemplos são substituídos pelos dados
  locais, que ficam somente no navegador. Importação repetida substitui o mesmo
  mês/ano/escopo. Valores negativos de lucro são permitidos; valores financeiros
  de entrada precisam ser não negativos. Clientes e inadimplência são posições
  no fim do mês e nunca são somados entre meses.
- Exportação CSV e relatório imprimível (salvar PDF pelo navegador).
- Mapa do Paraná focado no sul e sudeste, inspirado na captura fornecida do
  Supply Chain Simulator by Lovable: zoom, arraste, carteiras, seleção de cidade,
  rotas e simulação de atraso. As vendas e rotas são inteiramente ilustrativas;
  as linhas não representam navegação rodoviária. O atraso modifica apenas o
  prazo ilustrativo e a velocidade de animação, não estima prejuízos.
- Movimento reduzido do sistema respeitado, controle para pausar animação,
  navegação por teclado e diálogo nativo com foco contido.

## Dados reais e PDFs

Nenhum dado financeiro real, cliente real ou segredo está embutido no frontend.
Os gráficos iniciais têm uma identificação permanente de demonstração.

O cliente Supabase está preparado em `src/backend.js`, mas permanece desligado
sem as duas variáveis publicáveis em `.env.example`. Não existe cadastro público.
É necessário provisionar os acessos da equipe e políticas RLS antes de habilitar
o envio real de PDF. A interface não afirma que um arquivo foi enviado sem a
confirmação do Storage. Não há integração de leitura dos indicadores de produção
nesta versão: os indicadores usam CSV local ou demonstração.

Próxima integração: autorizar usuários por escopo (empresa/família); permitir
upload somente nos buckets autorizados; listar fila/documentos com RLS; expor
consolidados autenticados com seleção de um retrato por período, sem somar PDFs
sobrepostos. Vendas por cidade precisam de fonte com cidade/CNPJ/carteira.

## Design e referências

Figma e Lovable constavam instalados, mas não expuseram ferramentas executáveis
na sessão de criação. Esta implementação foi realizada diretamente no código;
nenhum arquivo Figma nem projeto Lovable foi criado por esta etapa. A captura
do Supply Chain Simulator foi utilizada como referência visual, sem copiar seu
código. A paleta é uma proposta; não havia manual de marca ou logo oficial.

Tokens: floresta `#15251f`, grafite `#101311`, lima suave `#d8e887`, âmbar
`#c0a066`, fundo `#f5f6f1`. DM Sans para interface e Instrument Serif em destaques.
O frasco foi gerado por imagem, sem marca, e está em `public/oil-hero.webp`.

Base geográfica: [IBGE — malhas simplificadas](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3).
Arquivo: `public/parana.geojson` (UF 41, intrarregião mesorregião, qualidade mínima).
Cidades são localizadas aproximadamente; carteiras, vendas e prazos são fictícios.
As fontes são distribuídas pelos pacotes @fontsource com licenças próprias.
Documentação de animação: [React Spring](https://www.react-spring.dev/).
