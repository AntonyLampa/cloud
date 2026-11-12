import boto3
import json
import os
import time
from datetime import datetime, timedelta, timezone

# Sessao usando as credenciais restritas do usuario agente-ops no Floci
session = boto3.Session(
    aws_access_key_id=os.environ.get("AGENTE_ACCESS_KEY", "AKIATDT44HM3TGV339AB"),
    aws_secret_access_key=os.environ.get("AGENTE_SECRET_KEY", "WG2o8LfqfmMxfPbNxnIHzCZNYHuC+ae9GXGYwc8x"),
    region_name="us-east-1"
)

ENDPOINT = "http://localhost:4566"
bedrock = session.client("bedrock-runtime", endpoint_url=ENDPOINT)
cw = session.client("cloudwatch", endpoint_url=ENDPOINT)
asg = session.client("autoscaling", endpoint_url=ENDPOINT)
logs = session.client("logs", endpoint_url=ENDPOINT)

MODELO = "anthropic.claude-3-haiku-20240307-v1:0"
LOG_GROUP = "/agente/operacoes-campo"
LOG_STREAM = f"execucao-{int(time.time())}"

def registrar_auditoria(evento: str, detalhes: dict):
    try:
        logs.create_log_group(logGroupName=LOG_GROUP)
    except Exception:
        pass
    try:
        logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
    except Exception:
        pass
    logs.put_log_events(
        logGroupName=LOG_GROUP,
        logStreamName=LOG_STREAM,
        logEvents=[{
            "timestamp": int(time.time() * 1000),
            "message": json.dumps({"evento": evento, **detalhes}, ensure_ascii=False, default=str)
        }]
    )

FERRAMENTAS = [
    {
        "toolSpec": {
            "name": "ler_metricas",
            "description": "Le estatisticas da metrica CPUUtilization no CloudWatch para um Auto Scaling Group.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "asg_name": {"type": "string", "description": "Nome do Auto Scaling Group"}
                    },
                    "required": ["asg_name"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "descrever_asg",
            "description": "Retorna configuracao atual do Auto Scaling Group (capacidade minima, maxima, desejada e instancias).",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "asg_name": {"type": "string", "description": "Nome do Auto Scaling Group"}
                    },
                    "required": ["asg_name"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "listar_atividades",
            "description": "Lista o historico recente de atividades de escalonamento do Auto Scaling Group.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "asg_name": {"type": "string", "description": "Nome do Auto Scaling Group"}
                    },
                    "required": ["asg_name"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "ajustar_capacidade",
            "description": "Altera a capacidade desejada (DesiredCapacity) do Auto Scaling Group. Exige aprovacao humana.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "asg_name": {"type": "string", "description": "Nome do Auto Scaling Group"},
                        "desired_capacity": {"type": "integer", "description": "Nova capacidade desejada"}
                    },
                    "required": ["asg_name", "desired_capacity"]
                }
            }
        }
    }
]

def executar(nome: str, entrada: dict):
    grupo = entrada.get("asg_name", "asg-campo")
    if nome == "ler_metricas":
        fim = datetime.now(timezone.utc)
        inicio = fim - timedelta(minutes=15)
        resp = cw.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "AutoScalingGroupName", "Value": grupo}],
            StartTime=inicio,
            EndTime=fim,
            Period=60,
            Statistics=["Average", "Maximum"]
        )
        pontos = sorted(resp.get("Datapoints", []), key=lambda x: x["Timestamp"])
        return {"datapoints": [{"timestamp": str(p["Timestamp"]), "avg": p.get("Average"), "max": p.get("Maximum")} for p in pontos]}

    elif nome == "descrever_asg":
        resp = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[grupo])
        grupos = resp.get("AutoScalingGroups", [])
        if not grupos:
            return {"erro": "ASG nao encontrado"}
        g = grupos[0]
        return {
            "AutoScalingGroupName": g["AutoScalingGroupName"],
            "MinSize": g["MinSize"],
            "MaxSize": g["MaxSize"],
            "DesiredCapacity": g["DesiredCapacity"],
            "Instances": len(g.get("Instances", []))
        }

    elif nome == "listar_atividades":
        resp = asg.describe_scaling_activities(AutoScalingGroupName=grupo, MaxRecords=5)
        return {"activities": [{"Description": a.get("Description"), "StatusCode": a.get("StatusCode")} for a in resp.get("Activities", [])]}

    elif nome == "ajustar_capacidade":
        nova_cap = int(entrada["desired_capacity"])
        asg.set_desired_capacity(AutoScalingGroupName=grupo, DesiredCapacity=nova_cap)
        return {"status": "sucesso", "asg_name": grupo, "nova_capacidade_desejada": nova_cap}

    return {"erro": f"Ferramenta desconhecida: {nome}"}

def main():
    msgs = [{
        "role": "user",
        "content": [{
            "text": (
                "O alarme 'cpu-alta-asg-campo' disparou por CPU acima de 80% no Auto Scaling Group 'asg-campo'. "
                "Use as ferramentas disponiveis para investigar as metricas, a configuracao atual do ASG e as atividades recentes. "
                "Se necessario, proponha e execute o ajuste de capacidade. "
                "Ao final, responda em portugues explicando: (1) o que aconteceu, (2) a causa provavel e (3) a acao recomendada ou executada."
            )
        }]
    }]

    iteracao = 0
    while iteracao < 6:
        resp = bedrock.converse(
            modelId=MODELO,
            system=[{"text": "Voce e um engenheiro de confiabilidade (SRE) AWS. Sempre investigue metricas e configuracao do ASG antes de alterar capacidade."}],
            messages=msgs,
            toolConfig={"tools": FERRAMENTAS}
        )
        msg = resp["output"]["message"]
        msgs.append(msg)

        if resp.get("stopReason") != "tool_use":
            print("\n=== DIAGNOSTICO FINAL DO AGENTE ===")
            print(msg["content"][0]["text"])
            registrar_auditoria("diagnostico_final", {"resposta": msg["content"][0]["text"]})
            break

        for bloco in msg["content"]:
            if "toolUse" in bloco:
                uso = bloco["toolUse"]
                nome = uso["name"]
                entrada = uso["input"]
                print(f"[Iteracao {iteracao + 1}] Agente solicitou ferramenta: {nome}({entrada})")

                if nome == "ajustar_capacidade":
                    aprovado = input(f"⚠️  APROVACAO HUMANA: Aprovar {nome} com {entrada}? [s/N] ").strip().lower()
                    if aprovado != "s":
                        resultado = {"erro": "acao negada pelo operador"}
                        registrar_auditoria("tool_negada", {"ferramenta": nome, "input": entrada})
                    else:
                        resultado = executar(nome, entrada)
                        registrar_auditoria("tool_executada", {"ferramenta": nome, "input": entrada, "resultado": resultado})
                else:
                    resultado = executar(nome, entrada)
                    registrar_auditoria("tool_executada", {"ferramenta": nome, "input": entrada, "resultado": resultado})

                print(f"   -> Resultado: {resultado}")
                msgs.append({
                    "role": "user",
                    "content": [{
                        "toolResult": {
                            "toolUseId": uso["toolUseId"],
                            "content": [{"json": resultado}]
                        }
                    }]
                })
        iteracao += 1

if __name__ == "__main__":
    main()