## Etapa 1 — Fundamentos de GenAI

### 1. Servidores MCP Locais (`stdio`) vs. Remotos (`http`)
De acordo com a documentação do `awslabs/mcp`, servidores MCP locais utilizam o transporte **stdio**, rodando diretamente na máquina do usuário como um subprocesso (via `uvx` ou container). Eles se comunicam pela entrada/saída padrão do sistema e têm acesso direto ao ambiente local, como arquivos e credenciais (`AWS_PROFILE=floci`). Já os servidores remotos utilizam **HTTP/SSE** e rodam hospedados na nuvem por meio de uma URL pública (como o `aws-knowledge`). Eles não acessam o disco ou ambiente local do cliente, servindo para consultar bases de conhecimento externas de forma centralizada.

### 2. Glossário de Conceitos Fundamentais (conectados ao AG822)
- **LLM (Large Language Model):** Modelo de aprendizagem profunda treinado em grandes volumes de dados para compreender e gerar texto. *Exemplo AWS:* Usar um LLM para traduzir logs de erro de uma instância **EC2** em explicações legíveis.
- **Prompt:** A instrução ou pergunta de entrada fornecida a um modelo para guiar a sua resposta. *Exemplo AWS:* Pedir ao assistente para gerar uma política JSON de menor privilégio para o **IAM**.
- **Contexto (Context Window):** O limite máximo de tokens que o modelo processa numa única interação (entrada + saída). *Exemplo AWS:* Enviar todo o código de um template CloudFormation de **VPC** dentro do limite da janela para auditoria.
- **RAG (Retrieval-Augmented Generation):** Técnica que busca informações em bases externas antes de gerar a resposta, reduzindo invenções. *Exemplo AWS:* Consultar manuais de arquitetura armazenados num bucket **S3** antes de responder dúvidas sobre redes.
- **Agente:** Sistema autônomo baseado em LLM capaz de planejar, decidir e executar ferramentas/APIs para resolver tarefas. *Exemplo AWS:* Um agente que lê alarmes do **CloudWatch** e ajusta a capacidade de um **Auto Scaling Group**.
- **MCP (Model Context Protocol):** Padrão aberto que conecta assistentes de IA a fontes de dados e APIs externas. *Exemplo AWS:* Conectar o VS Code ao servidor MCP de documentação oficial da AWS para validar regras de **Security Groups**.
- **Hallucination (Alucinação):** Fenômeno onde o modelo gera informações incorretas ou inventadas com alta confiança. *Exemplo AWS:* O modelo sugerir um parâmetro inexistente ao criar uma tabela no **DynamoDB**.
- **System Prompt:** Instruções de nível superior que definem o papel, regras e formato de saída do modelo. *Exemplo AWS:* Obrigar o modelo a responder apenas em JSON ao classificar eventos recebidos via **S3** e **Lambda**.
- **Embeddings:** Representações vetoriais (numéricas) de texto que capturam significado semântico para buscas por similaridade. *Exemplo AWS:* Indexar relatórios de inspeção salvos no **S3** para buscar incidentes semelhantes.
- **Temperature:** Parâmetro que controla a aleatoriedade das respostas (valores próximos de `0` geram respostas determinísticas). *Exemplo AWS:* Usar `temperature: 0` numa função **Lambda** que extrai dados estruturados de logs do **CloudWatch**.

### 3. Classificação dos Serviços AWS (IaaS, PaaS, SaaS)

| Serviço | Classificação | Justificativa |
| :--- | :--- | :--- |
| **Amazon Bedrock** | **PaaS** | Disponibiliza modelos de fundação via API gerida sem a necessidade de gerir servidores ou GPUs subjacentes, permitindo o desenvolvimento de aplicações sobre a plataforma. |
| **Bedrock AgentCore** | **PaaS** | Camada de orquestração gerida para a execução, identidade e observabilidade de agentes e ferramentas, abstraindo a infraestrutura do ambiente. |
| **Kiro** | **SaaS** | Aplicação/ambiente de desenvolvimento assistido por IA pronta a usar pelo utilizador final, focada na produtividade sem necessidade de hospedar ou configurar a plataforma. |

### 4. Mapeamento do Emulador Local (Floci)
- **Emulação Parcial:** 
  - **Bedrock Runtime:** Repassa chamadas da API `Converse` (incluindo *tool use*) para o Ollama local, mas o `InvokeModel` retorna apenas uma resposta fixa (*stub*) e a listagem de modelos não é emulada.
  - **Bedrock AgentCore:** Emula apenas o plano de controle (registro de recursos via CloudFormation), sem executar agentes de fato.
  - **IAM e CloudWatch:** O IAM só avalia políticas se `FLOCI_SERVICES_IAM_ENFORCEMENT_ENABLED=true` estiver ativo; o CloudWatch aceita métricas manuais, mas não gera métricas de EC2 automaticamente.
- **Não Emulado:** **Kiro**, **Agent Toolkit for AWS** (opera apenas em contas reais), Guardrails nativos e modelos proprietários fechados.
- **Por que o emulador imita a API, mas não a qualidade do modelo?** A API do Bedrock é apenas um contrato de comunicação HTTP/JSON padronizado, que o Floci intercepta e traduz para o formato do Ollama. Já a qualidade cognitiva depende da arquitetura da rede neural e da quantidade de parâmetros: um modelo local leve (como o `llama3.2` de 3B parâmetros rodando em CPU/RAM comum) tem capacidade de raciocínio e conhecimento muito inferiores aos modelos gigantes hospedados em clusters de GPUs na nuvem da AWS.

### 5. Questão de Checagem
> **Se um modelo responde com o nome de um serviço AWS que não existe, que técnica reduz esse problema e por quê?**
>
> **Resposta:** A técnica recomendada é o **RAG (Retrieval-Augmented Generation)** ou a integração via **MCP (Model Context Protocol)** conectado à documentação oficial da AWS. Eles reduzem as alucinações porque forçam o modelo a consultar dados reais e atualizados no catálogo oficial antes de formular a resposta, em vez de depender apenas da sua memória interna de treinamento.

## Etapa 2 — Assistentes de IA para Operar a AWS

### Diário de Prompts — Atividade 1: Consulta guiada por documentação (Com vs. Sem MCP)

#### 1. Execução COM servidores MCP ativos (`#aws-docs` e `#aws-knowledge`)
* **Prompt usado:**
  > `#aws-docs #aws-knowledge Explique a diferença entre Security Group e NACL na AWS, citando as páginas da documentação usadas.`
* **Ferramentas invocadas pelo agente:** `search_documentation` (via `aws-docs` / `aws-knowledge`).
* **Resumo da resposta da IA:**
  * **Security Group:** Filtro de tráfego no nível de instância/recurso (como EC2), *stateful* (o tráfego de retorno de uma conexão permitida é liberado automaticamente), aceita apenas regras de *allow* e atua como mecanismo principal de controle de acesso.
  * **NACL (Network Access Control List):** Filtro no nível de subnet, *stateless* (o tráfego de retorno precisa ser explicitamente permitido nas regras), aceita regras de *allow* e *deny* avaliadas em ordem numérica e funciona como camada adicional de defesa (*coarse-grain*).
  * **Páginas oficiais citadas:** *Security groups*, *Network ACLs* (e *Network ACL basics*) e *Infrastructure security in Amazon VPC*.

#### 2. Execução SEM servidores MCP ativos
* **Prompt usado:**
  > `Explique a diferença entre Security Group e NACL na AWS, citando as páginas da documentação usadas.`
* **Ferramentas invocadas pelo agente:** Nenhuma ferramenta MCP oficial chamada.
* **Resumo da resposta da IA:**
  * Manteve a distinção técnica correta entre nível de instância (*stateful*, apenas *allow*) e nível de subnet (*stateless*, *allow* e *deny* ordenados numericamente).
  * **Páginas citadas:** *Compare security groups and network ACLs*, *Control subnet traffic with network access control lists* e *Ensure internetwork traffic privacy in Amazon VPC*.

#### 3. Análise Crítica e Comparação (O que mudou)
* **Rastreabilidade e fundamentação:** Com os servidores MCP ativos (`#aws-docs` e `#aws-knowledge`), o assistente acionou explicitamente a API oficial de busca da documentação da AWS antes de responder, trazendo citações literais ancoradas nas páginas estruturais do guia da VPC.
* **Risco sem MCP:** Sem os servidores MCP, o modelo respondeu apoiado apenas no seu treinamento prévio (e busca genérica), alterando os títulos das referências para páginas mais específicas/dispersas. Em cenários reais com recursos lançados recentemente na AWS, depender apenas da memória do modelo sem MCP aumenta o risco de alucinação de parâmetros ou recomendação de configurações obsoletas.

### Diário de Prompts — Atividade 2: Inventário de Recursos (Teste do Endpoint)

* **Prompt usado:**
  > `Crie um script Python usando boto3 para listar todos os buckets S3, tabelas DynamoDB e usuários IAM desta conta.`
* **Resposta da IA (Arquivo gerado):**
  * O assistente gerou o script `list_aws_resources.py` utilizando os clientes padrão do SDK (`boto3.client('s3')`, `boto3.client('dynamodb')` e `boto3.client('iam')`) e iterando sobre as respostas das operações `list_buckets()`, `list_tables()` e `list_users()`.
* **Resultado da execução (`python list_aws_resources.py`):**
  * **Buckets S3:** `relatorios`, `imagens-drone`, `teste-floci`
  * **Tabelas DynamoDB:** `sensores`
  * **Usuários IAM:** `tecnico-campo`
* **Erros encontrados / Correções necessárias:**
  * Nenhum erro de sintaxe ou execução ocorreu no ambiente local; o script funcionou de primeira.
* **Análise Crítica (Risco de Endpoint em Produção):**
  * O código gerado **não fixou o `endpoint_url` (`http://localhost:4566`)** diretamente nos clientes `boto3`, delegando a resolução do destino às variáveis de ambiente e perfis configurados no sistema (`AWS_PROFILE=floci`).
  * **Impacto em ambiente real:** Embora essa abordagem mantenha o código portátil, ela representa um risco operacional crítico caso o script seja executado em uma máquina que possua credenciais reais da AWS configuradas (`~/.aws/credentials`) sem a variável `AWS_PROFILE=floci` ativa — nesse cenário, o código apontaria diretamente para a nuvem pública da AWS e listaria (ou modificaria, em scripts de escrita) recursos reais em produção.

  ### Diário de Prompts — Atividade 3: Menor Privilégio de Verdade (`IAM Enforcement`)

* **Configuração de infraestrutura:** Adicionada a variável `FLOCI_SERVICES_IAM_ENFORCEMENT_ENABLED: "true"` no `docker-compose.yml` para habilitar a validação real de políticas IAM no emulador.
* **Prompt usado:**
  > `Gere uma política IAM em JSON que permita apenas ler objetos (s3:GetObject) do bucket relatorios.`
* **Resposta da IA (Política gerada):**
  * O assistente apresentou duas opções corretas: uma estrita contendo apenas `"Action": ["s3:GetObject"]` com `"Resource": "arn:aws:s3:::relatorios/*"` e outra adicional incluindo `s3:ListBucket` sobre `"arn:aws:s3:::relatorios"`. Foi escolhida a política estrita (`politica-leitura.json`) por aderir rigorosamente ao princípio do menor privilégio.
* **Erros encontrados e correções:**
  * Ao reiniciar o container com `docker compose up -d` para aplicar o `IAM Enforcement`, o estado em memória do Floci foi limpo, gerando `NoSuchEntity` ao tentar anexar a política ao usuário `tecnico-campo`.
  * **Correção:** O bucket `relatorios`, o objeto `inspecao-001.txt` e o usuário `tecnico-campo` foram recriados antes da execução de `aws iam put-user-policy` e `aws iam create-access-key`.
* **Validação prática (com as credenciais do `tecnico-campo`):**
  * **Leitura (`aws s3 cp s3://relatorios/inspecao-001.txt -`):** Sucesso — retornou o conteúdo `Inspeção talhão 12: sem pragas`.
  * **Escrita (`aws s3 cp - s3://relatorios/bloqueado.txt`):** Bloqueada conforme esperado — retornou `An error occurred (AccessDenied) when calling the PutObject operation: User is not authorized to perform: s3:PutObject`.

  ## Etapa 3 — Infraestrutura como Código (IaC) Gerada por IA

### 1. Especificação Utilizada no Prompt
Foi solicitada a geração de um template CloudFormation em YAML (`vpc.yaml`) utilizando o assistente com o servidor MCP `aws-iac` (`awslabs.cfn-mcp-server`) conectado ao perfil `floci`, contemplando:
* Uma VPC (`10.0.0.0/16`) com sub-rede pública (`10.0.1.0/24`) e sub-rede privada (`10.0.2.0/24`);
* Um Internet Gateway anexado à VPC e tabela de rotas pública apontando `0.0.0.0/0` para ele;
* Um Security Group liberando apenas tráfego HTTP (porta `80`) de entrada;
* Uma instância EC2 `t3.micro` atuando como servidor web na sub-rede pública;
* Um bucket S3 (`relatorios-campo-iac`) e uma tabela DynamoDB (`triagem-iac`, chave primária `arquivo` do tipo `String`, modo `PAY_PER_REQUEST`).

### 2. Auditoria pelo Checklist e Correções Aplicadas

A validação sintática inicial com `uvx cfn-lint vpc.yaml` passou sem erros e o Security Group restringiu corretamente o ingresso à porta `80/tcp` (sem SSH `22` exposto para `0.0.0.0/0`). Contudo, a auditoria manual identificou **quatro problemas** no template original gerado pela IA:

| # | Problema identificado no template original da IA | Correção aplicada no `vpc.yaml` final |
|---|---|---|
| **1** | **Ausência de tags de governança e alocação de custo (Unidade II):** Os recursos possuíam apenas a tag `Name`, enquanto o bucket S3 e a tabela DynamoDB não tinham nenhuma tag. | Adicionados parâmetros `ProjectName` (`lab-genai-aws`) e `EnvironmentName` (`dev`) e aplicadas tags `Project` e `Environment` em todos os recursos suportados (`VPC`, `Subnets`, `IGW`, `RouteTable`, `SecurityGroup`, `EC2Instance`, `S3::Bucket` e `DynamoDB::Table`). |
| **2** | **Instância EC2 sem configuração de servidor web:** O template original provisionava uma instância EC2 ociosa, sem instruções de inicialização para servir conteúdo HTTP. | Incluído bloco `UserData` codificado com `Fn::Base64` na `EC2Instance` para instalar e habilitar o `nginx` e publicar uma página HTML inicial na porta `80`. |
| **3** | **Outputs incompletos:** Faltavam informações operacionais essenciais na seção `Outputs`, como o endereço IP público da instância web e o ARN da tabela DynamoDB. | Adicionados os outputs `InstancePublicIp` (usando `!GetAtt EC2Instance.PublicIp`) e `DynamoDbTableArn` (usando `!GetAtt TriagemTable.Arn`), totalizando 8 outputs válidos. |
| **4** | **Comportamento de atualização e exclusão no Floci (Limitação do emulador):** Ao executar `aws cloudformation deploy` sobre uma stack existente (`UpdateStack`) e depois `delete-stack`, o Floci falhou na atualização e travou a exclusão da VPC (`The vpc 'vpc-165a937c' has dependencies and cannot be deleted`) porque a instância EC2 ainda mantinha a ENI ativa. Além disso, como o caminho SSM `/aws/service/ami-amazon-linux-2023/x86_64/standard/latest` não existe no SSM local do Floci, o emulador gravou a string literal do caminho no `ImageId` da instância. | A instância EC2 foi encerrada explicitamente (`aws ec2 terminate-instances`) antes da remoção da stack, e o template revisado foi implantado do zero em uma nova stack (`lab-ia-v2`), confirmando o status `CREATE_COMPLETE` e os 8 outputs esperados. |

### 3. Resposta à Pergunta de Checagem
> *"Um template que implanta sem erro no Floci está pronto para a AWS real? Cite duas coisas que só a AWS verificaria."*

**Não.** Um deploy bem-sucedido no Floci valida a estrutura do CloudFormation e o fluxo básico de criação de recursos, mas não garante prontidão para produção na AWS real. Entre as verificações que **apenas a AWS real executa**, destacam-se:
1. **Existência real de AMIs e resolução efetiva de parâmetros SSM:** No Floci, o emulador aceitou `/aws/service/ami-amazon-linux-2023/x86_64/standard/latest` sem consultar um catálogo real de imagens, atribuindo o próprio caminho literal ao `ImageId`. Na AWS real, o CloudFormation resolve o parâmetro no SSM Parameter Store da região alvo e valida se a AMI existe, está disponível para a conta e é compatível com a arquitetura/tipo da instância (`t3.micro`).
2. **Cotas de serviço (*Service Quotas*), permissões IAM granulares e disponibilidade por AZ:** A AWS real verifica limites da conta (como número máximo de VPCs ou Elastic IPs na região), avalia cada ação de criação (`ec2:RunInstances`, `s3:CreateBucket`, `iam:PassRole`) contra as políticas IAM do executor e verifica capacidade física de instâncias na Availability Zone selecionada — além de gerar custos reais desde o momento em que os recursos entram no ar.

## Etapa 4 — Bedrock em Automação Orientada a Eventos

### 1. Arquitetura Implementada
Foi construído um pipeline serverless orientado a eventos para triagem automatizada de relatórios de inspeção agrícola:

```text
S3 (relatorios-campo / s3:ObjectCreated:*)
   └──► AWS Lambda (triagem / app.py - Python 3.12, timeout 120s)
           ├──► Amazon Bedrock Runtime (converse -> Ollama / llama3.2)
           └──► Amazon DynamoDB (tabela triagem)
```

* **Gatilho S3 (`relatorios-campo`):** Configurado via `put-bucket-notification-configuration` para disparar a função Lambda `triagem` automaticamente a cada novo arquivo enviado.
* **Função Lambda (`app.py`):** Lê o texto do relatório no S3, envia um prompt de sistema exigindo saída estritamente em JSON (`{"resumo": str, "urgencia": "baixa|media|alta"}`) para o Bedrock Runtime (`anthropic.claude-3-haiku-20240307-v1:0`, mapeado localmente para o `llama3.2` no Ollama) com `temperature=0` e `maxTokens=300`.
* **Tratamento de Resposta Inválida (Desafio Extra):** Implementado bloco `try/except` com limpeza de blocos Markdown e validação dos campos obrigatórios (`resumo` e `urgencia`). Caso o modelo pequeno retorne texto fora do formato JSON esperado, o item é registrado com `"urgencia": "revisao_humana"` em vez de gerar falha na execução da Lambda.
* **Menor Privilégio IAM:** A role `triagem-lambda` recebeu uma política inline (`triagem-minimo`) concedendo apenas `s3:GetObject` no bucket `relatorios-campo`, `bedrock:InvokeModel` no modelo alvo, `dynamodb:PutItem` na tabela `triagem` e permissões de escrita no CloudWatch Logs.

### 2. Resultados Obtidos no Teste (`aws dynamodb scan --table-name triagem`)

| Arquivo | Resumo gerado pelo modelo | Urgência | `tokens_in` | `tokens_out` |
|---|---|---|---|---|
| `relatorio1.txt` | Solo com umidade adequada e desenvolvimento vegetativo normal | `baixa` | 108 | 27 |
| `relatorio2.txt` | Infestação de lagarta-do-cartucho em 12% das plantas | `alta` | 122 | 31 |
| `relatorio3.txt` | Falta de irrigação em 40% das árvores de citros | `alta` | 131 | 30 |

* **Análise crítica do modelo local:** O modelo `llama3.2` (3B) seguiu rigorosamente o esquema JSON em todas as execuções sem precisar acionar o fallback de revisão humana. Porém, demonstrou comportamento conservador na calibração de severidade, classificando o `relatorio2.txt` (infestação inicial de 12% com recomendação preventiva) como `alta` em vez de `media`.

### 3. Diferenças no Floci vs. AWS Real
* **Injeção de Endpoint e Runtime:** O Floci executa a Lambda em um container Docker real e injeta automaticamente `AWS_ENDPOINT_URL`, permitindo que o `app.py` use `boto3.client("s3")` e `boto3.client("bedrock-runtime")` sem URLs fixas no código — idêntico ao código de produção na AWS.
* **Timeout e Latência:** Como a inferência roda localmente em CPU/RAM via Ollama, foi necessário elevar o `--timeout` da Lambda de 3 s (padrão) para `120` s. Na AWS real, o mesmo `app.py` rodaria sem alterações de código, trocando apenas o `modelId` para um modelo gerenciado habilitado na conta e contabilizando o custo real por token processado.

## Etapa 5 — Agentes e Automação Operacional

### 1. Cenário e Arquitetura do Agente
Foi implementado um agente operacional (`agente.py`) em Python utilizando a API `converse` do Bedrock (`toolConfig`) para diagnosticar incidentes de CPU alta no Auto Scaling Group `asg-campo` (`MinSize=1`, `MaxSize=4`, `DesiredCapacity=1`):

* **Monitoramento e Alerta:** Alarme CloudWatch `cpu-alta-asg-campo` configurado para disparar quando `CPUUtilization > 80%`, enviando notificação via tópico SNS (`alarme-cpu-campo`) para a fila SQS assinante (`fila-alertas-campo`).
* **Ferramentas Disponibilizadas ao Agente:**
  * `ler_metricas` (`cloudwatch:GetMetricStatistics` — leitura)
  * `descrever_asg` (`autoscaling:DescribeAutoScalingGroups` — leitura)
  * `listar_atividades` (`autoscaling:DescribeScalingActivities` — leitura)
  * `ajustar_capacidade` (`autoscaling:SetDesiredCapacity` — escrita, protegida por aprovação humana)
* **Controles de Segurança Implementados:**
  1. **Menor privilégio IAM:** Usuário dedicado `agente-ops` com política inline (`politica-agente-ops`) concedendo leitura apenas nas APIs de diagnóstico, invocação restrita ao modelo configurado e `autoscaling:SetDesiredCapacity` limitado exclusivamente ao ARN `arn:aws:autoscaling:us-east-1:000000000000:autoScalingGroup:asg-campo`.
  2. **Aprovação humana (*Human-in-the-Loop*):** Confirmação explícita `[s/N]` no terminal antes de qualquer execução de `ajustar_capacidade`.
  3. **Limite de iterações:** Laço limitado a `iteracao < 6` para prevenir loops infinitos.
  4. **Trilha de auditoria:** Registro estruturado em JSON de cada ferramenta solicitada, aprovada/negada e resposta final no CloudWatch Logs (`/agente/operacoes-campo`).

### 2. Análise Crítica da Execução no Floci (`llama3.2`)
Durante o teste simulando pico de CPU (`30% -> 60% -> 95%`), a execução revelou duas falhas clássicas de modelos pequenos em modo agente, comprovando a necessidade das barreiras de segurança:
1. **Tentativa de alteração fora de escala (`desired_capacity: 100`):** Na primeira iteração, o modelo invocou todas as ferramentas simultaneamente e tentou definir `desired_capacity: 100` antes de processar o retorno de `descrever_asg` (`MaxSize: 4`). A trava de aprovação humana (`N`) impediu o escalonamento indevido (`{'erro': 'acao negada pelo operador'}`).
2. **Alucinação pós-negação:** Mesmo recebendo o retorno explícito de que a ação foi negada pelo operador, o modelo redigiu o diagnóstico afirmando que a capacidade havia sido alterada de 1 para 2 instâncias — reforçando que a validação do estado real da infraestrutura deve sempre vir das APIs AWS/CloudWatch Logs e não apenas do texto gerado pelo LLM.

### 3. Resposta à Pergunta de Checagem
> *"O agente recomendou dobrar a capacidade porque 'a CPU estava em 95%', mas foi um único ponto publicado por você. Que ferramenta ou instrução faltou para evitar essa decisão?"*

Para evitar escalonamento precipitado baseado em um pico isolado (*spike*), faltaram dois elementos:
1. **Instrução de sistema (*System Prompt*) com política de estabilidade:** Exigir que o agente verifique a **tendência sustentada** ao longo de múltiplos períodos consecutivos (ex.: média acima de 80% por pelo menos 3 a 5 minutos seguidos) e confira o cooldown/atividades recentes antes de propor qualquer alteração de capacidade, tratando picos únicos como anomalias transitórias a serem apenas monitoradas.
2. **Ferramenta adicional de análise de histórico/logs da aplicação (`logs:FilterLogEvents` ou consulta de tráfego/requisições):** Permitir que o agente correlacione o pico de CPU com métricas de taxa de requisições (ALB/API) ou erros de aplicação (ex.: loop travado ou tarefa cron pontual), evitando escalar instâncias quando o gargalo não é aumento legítimo de carga.