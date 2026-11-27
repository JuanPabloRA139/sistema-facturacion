#!/usr/bin/env bash
# Ejecutar desde AWS CloudShell en la carpeta del proyecto.
set -euo pipefail
cd "$(dirname "$0")/.."
export AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""
cuenta=$(aws sts get-caller-identity --query Account --output text)
bucket="facturacion-lab-paquetes-${cuenta}-use1"
pila=facturacion-servicios-lab
tmp=$(mktemp -d)
mkdir -p "$tmp/app/certs"
python3 -m pip install -q --disable-pip-version-check --target "$tmp/app" -r requirements-aws.txt
# Incluir solo archivos de ejecución. El directorio de trabajo puede contener
# respaldos, datos locales o archivos de configuración privados.
mkdir -p "$tmp/app/backend" "$tmp/app/database" "$tmp/app/frontend"
for modulo in admin_aws api_aws auditoria_aws entrada identidades rds rfc servicios web_aws; do
  cp "backend/$modulo.py" "$tmp/app/backend/"
done
for sql in 01_catalogo 02_datos_catalogo 03_facturacion 04_procedimientos 06_operaciones 08_auditoria 09_identidades 10_permisos_runtime; do
  cp "database/$sql.sql" "$tmp/app/database/"
done
for recurso in panel.html panel.css panel.js acceso-aws.js rfc.js; do
  cp "frontend/$recurso" "$tmp/app/frontend/"
done
curl -fsSL --retry 2 https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem -o "$tmp/app/certs/rds.pem"
(cd "$tmp/app" && zip -qr "$tmp/lambda.zip" . -x '*__pycache__*')
if ! aws s3api head-bucket --bucket "$bucket" --expected-bucket-owner "$cuenta" 2>/dev/null; then
  aws s3api create-bucket --bucket "$bucket" --region us-east-1 >/dev/null
fi
aws s3api put-public-access-block --bucket "$bucket" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
key="lambda/$(sha256sum "$tmp/lambda.zip" | cut -c1-64).zip"
aws s3 cp "$tmp/lambda.zip" "s3://$bucket/$key" --only-show-errors
# Omitir un parámetro en una actualización conserva el rol existente.
roles=()
if [[ -n "${WEB_ROLE_NAME:-}" ]]; then roles+=("WebRoleName=$WEB_ROLE_NAME"); fi
if [[ -n "${API_ROLE_NAME:-}" ]]; then roles+=("ApiRoleName=$API_ROLE_NAME"); fi
if [[ -n "${ADMIN_ROLE_NAME:-}" ]]; then roles+=("AdminRoleName=$ADMIN_ROLE_NAME"); fi
aws cloudformation deploy --stack-name "$pila" --template-file infra/cloudformation.json --parameter-overrides ArtifactBucket="$bucket" ArtifactKey="$key" "${roles[@]}" --tags Proyecto=FacturacionServicios --no-fail-on-empty-changeset
# Una actualización puede encontrar la instancia de facturación detenida.
for salida in Database IdentityDatabase; do
  id=$(aws cloudformation describe-stacks --stack-name "$pila" --query "Stacks[0].Outputs[?OutputKey=='$salida'].OutputValue | [0]" --output text)
  estado=$(aws rds describe-db-instances --db-instance-identifier "$id" --query 'DBInstances[0].DBInstanceStatus' --output text)
  if [[ "$estado" == stopping ]]; then
    aws rds wait db-instance-stopped --db-instance-identifier "$id"
    estado=stopped
  fi
  if [[ "$estado" == stopped ]]; then
    aws rds start-db-instance --db-instance-identifier "$id" >/dev/null
  fi
  aws rds wait db-instance-available --db-instance-identifier "$id"
done
admin=$(aws cloudformation describe-stacks --stack-name "$pila" --query 'Stacks[0].Outputs[?OutputKey==`AdminFunction`].OutputValue | [0]' --output text)
resultado=$(aws lambda invoke --function-name "$admin" --cli-binary-format raw-in-base64-out --payload '{"accion":"inicializar"}' "$tmp/inicializacion.json" --query FunctionError --output text)
if [[ "$resultado" != None ]]; then echo "Inicialización pendiente. Revisar el log de la Lambda privada."; exit 1; fi
if [[ "${CREAR_CUENTAS_DEMO:-0}" == 1 ]]; then
  python3 infra/usuarios_demo.py
fi
aws cloudformation describe-stacks --stack-name "$pila" --query 'Stacks[0].Outputs[?OutputKey==`Url` || OutputKey==`Database` || OutputKey==`IdentityDatabase`].[OutputKey,OutputValue]' --output table
