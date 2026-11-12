import boto3
import json
import os

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")
tabela = boto3.resource("dynamodb").Table(os.environ["TABELA"])
MODELO = "anthropic.claude-3-haiku-20240307-v1:0"

def handler(event, context):
    for reg in event["Records"]:
        bucket = reg["s3"]["bucket"]["name"]
        chave = reg["s3"]["object"]["key"]
        texto = s3.get_object(Bucket=bucket, Key=chave)["Body"].read().decode("utf-8")

        resp = bedrock.converse(
            modelId=MODELO,
            system=[{
                "text": "Responda apenas com um objeto JSON válido, sem markdown ou texto extra, no formato: {\"resumo\": \"string\", \"urgencia\": \"baixa|media|alta\"}"
            }],
            messages=[{"role": "user", "content": [{"text": texto}]}],
            inferenceConfig={"maxTokens": 300, "temperature": 0},
        )

        resposta_texto = resp["output"]["message"]["content"][0]["text"].strip()
        uso = resp["usage"]

        # Tratamento para resposta JSON inválida (Desafio extra)
        try:
            # Remove eventuais blocos ```json ... ``` que modelos pequenos costumam adicionar
            limpo = resposta_texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            saida = json.loads(limpo)
            if "resumo" not in saida or "urgencia" not in saida:
                raise ValueError("Campos obrigatorios ausentes")
        except Exception as e:
            print(f"Aviso: JSON invalido retornado pelo modelo para {chave}: {resposta_texto} ({e})")
            saida = {
                "resumo": resposta_texto[:200],
                "urgencia": "revisao_humana"
            }

        tabela.put_item(Item={
            "arquivo": chave,
            **saida,
            "tokens_in": uso["inputTokens"],
            "tokens_out": uso["outputTokens"]
        })