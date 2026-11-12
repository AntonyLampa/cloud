import boto3


def list_s3_buckets(s3_client):
    response = s3_client.list_buckets()
    buckets = response.get("Buckets", [])
    if not buckets:
        print("Nenhum bucket S3 encontrado.")
        return []

    print("Buckets S3:")
    for bucket in buckets:
        print(f"- {bucket['Name']}")
    return buckets


def list_dynamodb_tables(dynamodb_client):
    paginator = dynamodb_client.get_paginator("list_tables")
    tables = []

    for page in paginator.paginate():
        tables.extend(page.get("TableNames", []))

    if not tables:
        print("Nenhuma tabela DynamoDB encontrada.")
        return []

    print("Tabelas DynamoDB:")
    for table_name in tables:
        print(f"- {table_name}")
    return tables


def list_iam_users(iam_client):
    paginator = iam_client.get_paginator("list_users")
    users = []

    for page in paginator.paginate():
        users.extend(page.get("Users", []))

    if not users:
        print("Nenhum usuário IAM encontrado.")
        return []

    print("Usuários IAM:")
    for user in users:
        print(f"- {user['UserName']}")
    return users


def main():
    session = boto3.Session()

    print("Conectando à AWS...")

    try:
        s3_client = session.client("s3")
        dynamodb_client = session.client("dynamodb")
        iam_client = session.client("iam")

        print("\n=== Recursos da conta AWS ===")
        list_s3_buckets(s3_client)
        print()
        list_dynamodb_tables(dynamodb_client)
        print()
        list_iam_users(iam_client)

    except Exception as exc:
        print(f"Erro ao acessar a AWS: {exc}")
        raise


if __name__ == "__main__":
    main()
